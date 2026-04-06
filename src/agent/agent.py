import re
import sys
import json
from typing import List, Dict, Any
from pathlib import Path

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
        Final Answer: [Your comprehensive final answer to the user in Vietnamese].

        Example of tool usage:
        Thought: I need to check the weather.
        Action: get_weather_forecast
        Action Input: {{"location": "Gia Lâm", "date": "30/04"}}
        """

    def run(self, user_input: str) -> str:
        """
        TODO: Implement the ReAct loop logic.
        1. Generate Thought + Action.
        2. Parse Action and execute Tool.
        3. Append Observation to prompt and repeat until Final Answer.
        """
        logger.log_event("AGENT_START", {"input": user_input, "model": self.llm.model_name})
        
        current_prompt = user_input
        steps = 0

        while steps < self.max_steps:
            logger.info(f"--- Step {steps + 1} ---")
            
            # 1. Generate LLM response
            response = self.llm.generate(prompt=current_prompt, system_prompt=self.get_system_prompt())
            llm_text = response.get('content', '')
            
            logger.info(f"LLM Output:\n{llm_text}")
            
            # Append LLM's thought/action to the current_prompt
            current_prompt += f"\n{llm_text}\n"
            
            # 2. Check if Agent reached a Final Answer
            if "Final Answer:" in llm_text:
                final_answer = llm_text.split("Final Answer:")[-1].strip()
                logger.log_event("AGENT_END", {"status": "success", "steps": steps + 1})
                return final_answer
                
            # 3. Parse Thought/Action from result using Regex
            # Looks for Action: tool_name
            action_match = re.search(r"Action:\s*([a-zA-Z0-9_]+)", llm_text)
            # Looks for Action Input: {"key": "value"}
            action_input_match = re.search(r"Action Input:\s*(\{.*?\})", llm_text, re.DOTALL)
            
            if action_match and action_input_match:
                tool_name = action_match.group(1).strip()
                action_input_str = action_input_match.group(1).strip()
                
                logger.log_event("TOOL_CALLED", {"tool": tool_name, "args": action_input_str})
                
                # 4. Call tool -> Append Observation
                observation = self._execute_tool(tool_name, action_input_str)
                current_prompt += f"Observation: {observation}\n"
                logger.info(f"Observation: {observation}")
                
            else:
                # Phase 4: Failure Analysis (Handling format hallucinations)
                error_msg = "Error: Invalid format. Please provide 'Action:' and 'Action Input:' (as JSON)."
                current_prompt += f"Observation: {error_msg}\n"
                logger.error(f"Format parsing failed on LLM output.")

            steps += 1
            
        logger.log_event("AGENT_END", {"steps": steps})
        return "Xin lỗi, tôi đã mất quá nhiều thời gian suy nghĩ mà chưa tìm ra câu trả lời cuối cùng."

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
