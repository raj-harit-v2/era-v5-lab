# Public dashboard glossary

| Term | Meaning |
| --- | --- |
| Token | A piece of text that the model reads or predicts, such as part of a word or a punctuation mark. |
| Training step | An update to the model during training. |
| Training loss (next-token) | A measure of how well the model predicts the next token in its training text. Lower loss means better predictions on that text. |
| Training loss (step-bucket mean) | The average next-token training loss over a group of consecutive training steps. |
| Held-out validation loss | Next-token prediction loss on text set aside from training, averaged per token. Compare runs that use the same tokenizer and validation text. A tokenizer splits text into tokens. |
| Nat | A unit for measuring prediction loss. The validation loss chart shows loss in nats per token. |
| Bit | A unit for measuring information. A bit is a little smaller than a nat. |
| Byte | A unit of stored text. In UTF-8, the standard way to store text, a character takes one or more bytes. |
| Script | A writing system, such as Latin for English or Devanagari for Hindi. |
| Held-out validation bits per byte | Prediction loss on text set aside from training, measured in bits per byte of text. This lets readers compare runs that split text into tokens differently when the runs use the same validation text. |
| Learning rate schedule | The pattern of changes to the learning rate during training. The learning rate helps set the size of each update to the model. |
| Optimiser | The method that turns what the model learns from each training step into an update of the model. |
| Warmup, steady state and decay | Phases that a learning rate schedule can have. Warmup raises the learning rate at the start, steady state holds it, and decay lowers it. |
| Tokens per byte | The token count divided by the size of the same text in bytes. A lower value means the same text is split into fewer tokens. |
| Language slice | The part of the text that is in one language. |
| Language code | A short code that names a language, such as hi for Hindi or ta for Tamil. In the tokens per byte chart, the line named all covers every language together. |
| Mixture-of-experts load balance | In the least balanced layer, divide the busiest expert's token assignments by the average number of assignments per expert. An expert is a part of the model that processes selected tokens. The value is lowest when every expert gets the same share of tokens. |
| Routed expert | An expert that gets only the tokens that the model sends to it. The model picks a few experts for each token. |
