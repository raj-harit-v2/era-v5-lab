# Public dashboard glossary

| Term | Meaning |
| --- | --- |
| Token | A piece of text that the model reads or predicts, such as part of a word or a punctuation mark. |
| Training step | An update to the model during training. |
| Training loss (next-token) | A measure of how well the model predicts the next token in its training text. Lower loss means better predictions on that text. |
| Training loss (step-bucket mean) | The average next-token training loss over a group of consecutive training steps. |
| Held-out validation loss | Next-token prediction loss on text set aside from training, averaged per token. Compare runs that use the same tokenizer and validation text. A tokenizer splits text into tokens. |
| Held-out validation bits per byte | Prediction loss on text set aside from training, measured in bits per byte of text. This lets readers compare runs that split text into tokens differently when the runs use the same validation text. |
| Learning rate schedule | The pattern of changes to the learning rate during training. The learning rate helps set the size of each update to the model. |
| Tokens per byte | The token count divided by the size of the same text in bytes. A lower value means the same text is split into fewer tokens. |
| Mixture-of-experts load balance | In the least balanced layer, divide the busiest expert's token assignments by the average number of assignments per expert. An expert is a part of the model that processes selected tokens. |
