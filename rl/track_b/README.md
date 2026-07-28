# Track B

Track B is the advanced-policy path. Its first frozen use is the bounded
Inkling L4 branch in
[`representation_training_v1`](../studies/representation_training_v1/README.md).
The study owns the stage, reward, schedule, checkpoint, evaluation, and spend
contract; Track B owns only the Inkling-specific runtime bridge.

`tml_shim.py` is the runtime bridge needed by that future launcher. It registers
native TMLv0 support only for `thinkingmachines/Inkling`, requires an explicit
programmatic thinking-effort value, keeps reasoning separate from final text,
and refuses every supervised rendering entrypoint. Importing it does not
register anything or create a Tinker client.

The shared study launcher imports this bridge only for an Inkling RL stage.
Inkling remains RL-only and never receives an SFT answer serialization.
