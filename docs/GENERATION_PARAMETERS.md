# Model and generation settings

The project calls `http://localhost:11434/api/generate` using `qwen2.5:3b`.
Each run saves the installed model digest, quantization, Ollama/Python versions,
hardware, model template and system message in its `.metadata.json` file.
The report reads those snapshots. Use those exact values for the video; a tag
alone does not establish the installed quantization.

## Explicit settings

| Parameter | Value |
|---|---|
| temperature | 0 in the primary experiment; 1.0 in the temperature experiment |
| seed | 42 |
| num_ctx | 4096 |
| num_predict | 1024 |
| top_k | 40 |
| top_p | 0.9 |
| min_p | 0 |
| repeat_penalty | 1.2 |
| repeat_last_n | 128 |
| presence_penalty | 0 |
| frequency_penalty | 0 |
| stream | false |
| format | omitted in prompt-only; JSON_SCHEMA object in schema mode |

The token limit is larger than a short classification response because all entity
names are requested. It still can truncate an unusually long response; failures
remain in the evaluation. HTTP timeouts are 5 seconds for connection and 300 seconds
for reading a response. Timeouts are client limits, not sampling settings.

## Runtime choices

No custom system/template override, raw prompt mode, context history, custom stop
list, tools or thinking setting is sent. Saved model template/system and built-in
end tokens apply. GPU allocation and CPU thread count are automatic. No
speculative draft model is configured by this code.

For recorded Ollama 0.40.2, omitted `num_keep` has source default 4 and the legacy
`typical_p` field has source default 1.0; batch default is 512. These are source
settings, not independently measured runtime values. See the
[versioned source](https://github.com/ollama/ollama/blob/v0.40.2/api/types.go#L1087).
For a different Ollama version, inspect that version and make a new complete study;
do not silently mix its results with the recorded configuration.

The four runs must share model, prompt, schema and environment. Only `format`
changes between modes; only temperature changes in a temperature pair. A fixed
seed improves reproducibility but does not guarantee identical results across
hardware or runtime changes.
