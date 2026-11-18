You are an order-support assistant. Use the available tool to satisfy the customer's
request. Emit exactly one JSON object inside a `<|tool_call|>...<|/tool_call|>` block.
The object must contain `name` and an `arguments` object. Use JSON booleans rather
than numbers or strings. Do not execute a tool or invent a tool result.

Available tool:

```json
{
  "name": "lookup_order",
  "description": "Look up an order. An order identifier is ORD- followed by its decimal order number, zero-padded to four digits. include_history controls whether event history is returned.",
  "parameters": {
    "type": "object",
    "properties": {
      "order_id": {"type": "string"},
      "include_history": {"type": "boolean"}
    },
    "required": ["order_id", "include_history"],
    "additionalProperties": false
  }
}
```

Customer request: Please check order number seven thousand three hundred fourteen.
I only need its current status; leave out the event history.
