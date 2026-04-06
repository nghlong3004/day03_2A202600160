# Combined Evaluation Summary

## 1) Chatbot 10-case Summary

| Metric | Value |
| :--- | ---: |
| Total cases | 10 |
| Passed cases | 10 |
| Pass rate (%) | 100.0 |
| Avg Correctness | 2.0 |
| Avg Completeness | 1.8 |
| Avg Safety | 2.0 |
| Avg Latency (ms) | 3560.7 |
| Avg Total Tokens | 279.9 |

## 2) Hallucination Stress Summary

| Metric | Value |
| :--- | ---: |
| Total suites | 1 |
| Avg Hallucination Score (/8) | 6.0 |
| Max Score | 6 |
| Min Score | 6 |

## 3) Weak Cases (Priority)

- M2: completeness=1, safety=2, missed=['ket_luan']
- F2: completeness=1, safety=2, missed=['khong_tool']

## 4) Stress Suites Need Improvement

- Không có suite dưới ngưỡng cảnh báo.

## 5) Prioritized Limitations

1. Hiệu năng hallucination stress chưa cao, cần cải tiến state tracking và uncertainty handling.
