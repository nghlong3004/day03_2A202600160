import re
import sys
import json
from typing import List, Dict, Any
from pathlib import Path
from time import perf_counter

project_root = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(project_root))

from core.llm_provider import LLMProvider
from telemetry.logger import logger

class ReActAgent:
    """
    SKELETON: A ReAct-style Agent that follows the Thought-Action-Observation loop.
    Students should implement the core loop logic and tool execution.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        TODO: Implement the system prompt that instructs the agent to follow ReAct.
        Should include:
        1.  Available tools and their descriptions.
        2.  Format instructions: Thought, Action, Observation.
        """
        tool_descriptions = "\n".join([f"- {t['name']}: {t['description']}" for t in self.tools])
    
        return f"""You are a helpful Camping Assistant planning trips in Vietnam.
        You have access to the following tools:

        {tool_descriptions}

        You MUST follow this exact format for every step:

        Thought: Consider what you need to do next to answer the user's request.
        Action: The name of the tool to use (must be one of the tools listed above).
        Action Input: A valid JSON object containing the parameters for the tool.
        Observation: The result from the tool (Wait for the system to provide this, DO NOT generate it yourself).

        When you have gathered enough information to fully answer the user, use this format:
        Thought: I have all the information needed.
        Final Answer: [Your comprehensive final answer to the user in Vietnamese, written as clean plain text only, with no Markdown symbols such as **, *, #, -, or code fences].

        Example of tool usage:
        Thought: I need to check the weather.
        Action: get_weather_forecast
        Action Input: {{"location": "Gia Lâm", "date": "30/04"}}
        """

    def run(self, user_input: str) -> str:
        return self.run_with_metadata(user_input)["answer"]

    def run_with_metadata(self, user_input: str) -> Dict[str, Any]:
        """
        Execute the ReAct loop and return both the final answer and structured
        metadata for observability in the demo UI.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})

        started_at = perf_counter()
        current_prompt = user_input
        steps = 0
        trace: List[Dict[str, Any]] = []
        tool_calls: List[Dict[str, Any]] = []
        usage_totals = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        provider_name = "unknown"
        final_answer = ""
        executed_steps = 0

        while steps < self.max_steps:
            logger.info(f"--- Step {steps + 1} ---")
            executed_steps = steps + 1

            response = self.llm.generate(prompt=current_prompt, system_prompt=self.get_system_prompt())
            llm_text = response.get('content', '')
            provider_name = response.get("provider", provider_name)
            usage = response.get("usage", {})
            for key in usage_totals:
                usage_totals[key] += int(usage.get(key, 0) or 0)

            logger.info(f"LLM Output:\n{llm_text}")

            current_prompt += f"\n{llm_text}\n"

            thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|\nFinal Answer:|$)", llm_text, re.DOTALL)
            if thought_match:
                trace.append(
                    {
                        "type": "thought",
                        "title": "Suy nghĩ",
                        "content": thought_match.group(1).strip(),
                        "step": steps + 1,
                    }
                )

            if "Final Answer:" in llm_text:
                final_answer = llm_text.split("Final Answer:")[-1].strip()
                trace.append(
                    {
                        "type": "final",
                        "title": "Câu trả lời cuối cùng",
                        "content": final_answer,
                        "step": steps + 1,
                    }
                )
                logger.log_event("AGENT_END", {"status": "success", "steps": steps + 1})
                break

            action_match = re.search(r"Action:\s*([a-zA-Z0-9_]+)", llm_text)
            action_input_match = re.search(r"Action Input:\s*(\{.*?\})", llm_text, re.DOTALL)

            if action_match and action_input_match:
                tool_name = action_match.group(1).strip()
                action_input_str = action_input_match.group(1).strip()

                trace.append(
                    {
                        "type": "action",
                        "title": "Hành động",
                        "content": f"{tool_name}\n{action_input_str}",
                        "step": steps + 1,
                    }
                )
                logger.log_event("TOOL_CALLED", {"tool": tool_name, "args": action_input_str})

                observation = self._execute_tool(tool_name, action_input_str)
                tool_calls.append(
                    {
                        "name": tool_name,
                        "arguments": action_input_str,
                        "observation": observation,
                        "step": steps + 1,
                    }
                )
                current_prompt += f"Observation: {observation}\n"
                trace.append(
                    {
                        "type": "observation",
                        "title": "Quan sát",
                        "content": observation,
                        "step": steps + 1,
                    }
                )
                logger.info(f"Observation: {observation}")

            else:
                error_msg = "Error: Invalid format. Please provide 'Action:' and 'Action Input:' (as JSON)."
                current_prompt += f"Observation: {error_msg}\n"
                trace.append(
                    {
                        "type": "observation",
                        "title": "Quan sát",
                        "content": error_msg,
                        "step": steps + 1,
                    }
                )
                logger.error(f"Format parsing failed on LLM output.")

            steps += 1

        if not final_answer:
            logger.log_event("AGENT_END", {"steps": steps})
            final_answer = "Xin lỗi, tôi đã mất quá nhiều thời gian suy nghĩ mà chưa tìm ra câu trả lời cuối cùng."

        latency_ms = int((perf_counter() - started_at) * 1000)
        return {
            "mode": "agent",
            "answer": final_answer,
            "provider": provider_name,
            "model": self.llm.model_name,
            "latency_ms": latency_ms,
            "tool_calls": tool_calls,
            "trace": trace,
            "usage": usage_totals,
            "steps": executed_steps or 1,
        }

    def _execute_tool(self, tool_name: str, args: str) -> str:
        """
        Helper method to execute tools by name.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                try:
                    # Parse string to JSON dictionary
                    kwargs = json.loads(args)
                    
                    # Assume 'func' key contains the callable python function
                    executable_func = tool.get('func')
                    
                    if executable_func:
                        # Execute and return stringified result
                        result = executable_func(**kwargs)
                        return str(result)
                    else:
                        return f"Error: Tool '{tool_name}' is defined but has no executable function attached."
                        
                except json.JSONDecodeError as e:
                    logger.error(f"JSON Parsing Error: {str(e)}")
                    return f"Error: Action Input is not valid JSON. Detail: {str(e)}"
                except Exception as e:
                    logger.error(f"Tool Execution Error: {str(e)}")
                    return f"Error executing tool '{tool_name}': {str(e)}"
        return f"Error: Tool '{tool_name}' not found. Please use a provided tool."
