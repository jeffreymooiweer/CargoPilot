"""The assistant: the existing wizard, driven through natural language.

No regulatory knowledge lives here, and none may ever arrive. The assistant
translates in two directions — user text into structured patches on the wizard
state, and the backend's own open questions into something a chat can ask —
and everything it writes runs through the same services and validators the
wizard uses. The language model (optional, phase 23) only does the
translating; with no model present the chain still works, on the parser and
the four-language texts the application already has.
"""
