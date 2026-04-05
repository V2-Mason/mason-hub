---
globs: "scripts/**,agents/**,data/**"
---

# Anti-Rationalization Checklist

Stop immediately when you catch yourself thinking:
- "This is too simple to test" -- simple code also has bugs
- "I'm confident" -- confidence is not evidence, run verification
- "Just this once, skip it" -- no exceptions
- "I already changed the code, should be fine" -- changed != correct
- "Linter passed, good enough" -- linter is not a compiler or test suite
- "I ran it before" -- before != now

# Lesson Format (after completing non-trivial tasks)

Gap types (mandatory field):
- Config error -- fix immediately
- System capability gap -- file trigger action, triage needed
- Documentation update -- update the relevant file
- Integration gap -- file trigger action, triage needed
- Pure knowledge -- retain as-is