Route to a person if:

* If it was working fine and just stopped, especially after an update or with zero changes on their end, it's probably a bug.

* If they followed the instructions and are still stuck, don't loop them back to the bot.

* Anytime someone needs to look into their billing, plan details, account details, or their specific n8n Cloud instance.

* If the fix relies on how n8n handles weird limits, timing, or under-the-hood behavior that isn't explicitly in the manual.

* If a wrong guess could cause a production outage, lose data, or cost them money (like migrations or overwriting data), a human needs to guide them.

Let the bot handle it if:

* The exact fix is already clearly spelled out in the documentation.

* It's a general technical question (like formatting JSON, writing SQL, HTTP requests, or basic API logins).

When in doubt: Route it to a person.
