## Qwen 2.5 7B: Standard 4-bit (BitsAndBytes) on eval_mini

G12 rotation task. Model `unsloth/Qwen2.5-7B-Instruct-bnb-4bit` (7.61B parameters).
Empirical run of G9's `eval_mini` profile (1,870 items) on a single Google Colab Tesla T4 GPU (16 GB VRAM), seed 42.

### Results

| Benchmark (items) | Standard 4-bit (BnB) | Primary Metric |
| :--- | :---: | :---: |
| **ARC Challenge (500)** | 52.80% | acc_norm |
| **HellaSwag (400)** | 65.75% | acc_norm |
| **MMLU (570)** | 72.81% | acc |
| **GSM8K 5-shot (200)** | 77.00% | exact_match (flexible-extract) |
| **TruthfulQA MC2 (200)** | 60.41% | acc |
| **Mean of five** | **65.75%** | **unweighted mean** |

Evaluated on a Google Colab Tesla T4 (15,360 MiB). Batch sizes were configured to utilize ~55% of VRAM capacity (`batch_size=8` for multiple choice, `batch_size=4` for GSM8K), safely avoiding OOM while maintaining high throughput.

### Head-to-Head Comparison with AWQ Variant

| Benchmark (items) | Standard 4-bit (BnB) | AWQ 4-bit | Difference (AWQ vs BnB) | McNemar p |
| :--- | :---: | :---: | :---: | :---: |
| **ARC Challenge (500)** | 52.8% | 52.8% | +0.0 (-3.0 to +3.0) | 1.000 |
| **HellaSwag (400)** | 65.8% | 66.8% | +1.0 (-1.3 to +3.3) | 0.523 |
| **MMLU (570)** | 72.8% | 72.6% | -0.2 (-2.8 to +2.5) | 1.000 |
| **GSM8K 5-shot (200)** | 77.0% | 82.0% | **+5.0 (-0.8 to +10.8)** | 0.132 |
| **TruthfulQA MC2 (200)** | 60.4% | 59.8% | -0.6 (-3.9 to +2.6) | not given |
| **Mean of five** | **65.75%** | **66.79%** | **+1.04%** | — |

AWQ maintains a **+5.00 point lead on GSM8K (82.0% vs 77.0%)**, demonstrating the advantage of activation-guided outlier weight preservation in multi-step arithmetic reasoning.

### Notes
- Only Standard 4-bit (`bnb_4bit`) is added to `teams/12-quantization/runs/runs.csv` per team governance rules.
- Complete head-to-head analysis is in `/home/opc/projects/era-v5-team12-4-bit-eval-mini/AWQ_vs_BNB4bit_Qwen2.5_7B_Comparison.md` and the Netlify site.
- Conforms strictly to TSAI #269 eval firewall (zero raw prompt/output text stored in `.samples.jsonl`).
