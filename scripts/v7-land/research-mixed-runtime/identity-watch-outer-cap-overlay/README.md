# Identity child monitoring correction

The identity worker no longer rejects a valid result using a child-reported high-water mark that may include the parent's pre-exec peak. An outer process-group watchdog must still enforce the memory cap; the child timeout, output-size limit, and result validation remain. The synthetic regression reproduces the inherited high-water case and rejects malformed output. Apply over the corresponding named-identity runtime and repin code in each new request.
