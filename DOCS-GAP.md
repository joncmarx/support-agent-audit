# Docs-gap report: where the fix lived for 240 n8n community questions

Every question in this audit came from the [n8n community forum](https://community.n8n.io) and had an accepted answer from someone other than the asker. Two AI labelers from different companies, a blind tie-breaker and a human reading of their disagreements decided where each fix lived. 69 of the 240 questions (29%) needed something the docs don't have. This report sorts them into what n8n could write, what a bot should be told, and what will always need a person.

It is written to be useful to n8n's team. The docs are open source and held the fix for 97 of these 240 questions outright, and the forum answers that make up the answer key are the community's work. The point is that support conversations already show which articles to write next.

| Where the fix lived | Practice | Test | Holdout | All 240 |
|---|---|---|---|---|
| In n8n's docs | 22 | 35 | 40 | **97** |
| General technical know-how | 11 | 32 | 31 | **74** |
| n8n know-how the docs don't have | 6 | 19 | 22 | **47** |
| A known bug or release issue | 3 | 9 | 3 | **15** |
| Only n8n staff can act | 1 | 2 | 4 | **7** |

Fix summaries are the labeler's own one-line paraphrase of the accepted answer, not the forum text. Follow the link to read the thread and credit its author.

## Articles n8n could write (47)

The fix is n8n-specific know-how that the docs (pinned commit) don't contain. A forum member knew it. An article would let a docs bot answer next time.

### AI Agent, memory and vector nodes (7)

**Write:** One troubleshooting page for the AI Agent cluster: how memory session keys resolve when tools run, why binary data can't cross the agent-to-tool boundary (and the reference pattern instead), setting embedding dimensions, routing a Model Selector on $error, the fixed-vs-expression Type field in Message a Model, and what Evaluate All needs.

| Question | Set | The fix that worked |
|---|---|---|
| [Error in my memory nodes](https://community.n8n.io/t/error-in-my-memory-nodes/297496) | Test | Extract the sender ID into a sessionId field in a Set node before the AI Agent, then set the memory node's Key parameter to {{ $json.sessionId }} so it resolves when the agent runs tools. |
| [AI Agent Node Won’t Pass Binary Data to HTTP Request Node](https://community.n8n.io/t/ai-agent-node-won-t-pass-binary-data-to-http-request-node/261291) | Holdout | Because the agent calls tools with a JSON-only payload, binary data cannot cross the agent-to-tool boundary, so the file must be handled outside the agent: either store it and pass a reference (URL/path/ID) through the agent, or run the binary HTTP Request in a normal HTTP Request node after or outside the agent. |
| [Vector nodes store wrong dimension - always 192](https://community.n8n.io/t/vector-nodes-store-wrong-dimension-always-192/293231) | Holdout | In the Embeddings OpenAI node, add the Dimensions option and set it to 768 by switching the field to Expression mode and typing 768, so the node requests and stores 768-dimension vectors from the LM-Studio backend instead of 192. |
| [OpenAI "Message a model" node fails with "Missing fileName parameter" error](https://community.n8n.io/t/openai-message-a-model-node-fails-with-missing-filename-parameter-error/306497) | Holdout | Switch the Type field of Message 1 from Expression mode back to Fixed, select 'Text' in the Type dropdown so the Prompt field appears, then enter the prompt text there (and set the Model). |
| [Model Selector node as fallback mechanism when primary LLM fail](https://community.n8n.io/t/model-selector-node-as-fallback-mechanism-when-primary-llm-fail/273736) | Holdout | Configure the Model Selector rules to test the error with the {{ $error.message }} expression (e.g. contains 429 or rate limit, plus a catch-all rule on {{ $error }} not being empty) instead of $json.execution.error.message, so each rule routes to the fallback model. |
| [Is it possible, AI send product image to user](https://community.n8n.io/t/is-it-possible-ai-send-product-image-to-user/296659) | Holdout | Use a single AI agent that outputs structured JSON (intent, product_id), route on it with a Switch node, look up the product image URL in Airtable, and send it through the Messenger Send API as an image attachment. Because Airtable attachment URLs are signed and expire, upload the image to Messenger's attachment_upload endpoint (or re-host it on stable storage) first. |
| [Evaluations not working - runs first data point only](https://community.n8n.io/t/evaluations-not-working-runs-first-data-point-only/299625) | Holdout | Make sure the workflow uses the 'When fetching a dataset row' evaluation trigger with a valid dataset linked to it (unlink and relink the dataset if needed), because the 'Evaluate All' button only appears in that case. |

### Public API, CLI and credentials by API (7)

**Write:** An API cookbook: the list endpoint omits description (use Get), description is top-level on PUT, Custom Auth credentials take json as a string, which API key can act on which project in 2.x, bootstrapping an instance for CI, what publish:workflow's warning means, and how credential names auto-number.

| Question | Set | The fix that worked |
|---|---|---|
| [Warning messages when calling n8n publish:workflow](https://community.n8n.io/t/warning-messages-when-calling-n8n-publish-workflow/266219) | Practice | Ignore the CLI warning: workflow definitions live in the database and n8n loads the published version at execution time, so publishing via `n8n publish:workflow` takes effect on the next execution without a restart in a standard main-mode setup. |
| [Workflow description missing in API resonse?](https://community.n8n.io/t/workflow-description-missing-in-api-resonse/309760) | Practice | Use the n8n node's 'Get Many' to list the tagged workflows, then pass each workflow ID to a second n8n node set to 'Get', because GET /workflows/{id} returns the full object including description while the list endpoint omits it. |
| [Is there a way to put description in the workflow with the n8n API](https://community.n8n.io/t/is-there-a-way-to-put-description-in-the-workflow-with-the-n8n-api/298502) | Test | Send a PUT request to /api/v1/workflows/{id} with a top-level 'description' field in the body (not inside meta), alongside name, nodes, connections, and a cleaned settings object that contains only accepted fields such as executionOrder. |
| [N8n and automation testing](https://community.n8n.io/t/n8n-and-automation-testing/294401) | Test | Start n8n with a fixed N8N_ENCRYPTION_KEY, call POST /rest/owner/setup once to create the owner, then call POST /rest/me/api-keys to mint an API key, and snapshot and reuse the Postgres volume across CI runs. |
| [Credentials - Custom Auth with API](https://community.n8n.io/t/credentials-custom-auth-with-api/274894) | Holdout | In the PATCH body, set data.json to a stringified JSON string (e.g. "{\"headers\":{\"Authorization\":\"Bearer 1234\"}}") instead of a nested object, because the Custom Auth credential stores its json field as a string. |
| [API n8n - Version 2.X](https://community.n8n.io/t/api-n8n-version-2-x/273525) | Holdout | Use the API key of the account that owns the workflow (or the project it belongs to) to deactivate it, since in 2.x the Owner's API key lacks the scope to act on workflows in other users' personal projects; alternatively upgrade to a licensed plan with RBAC/project-level access. |
| [Credential name auto-increment seems global for custom credentials, but per-person for some built-ins (OpenAI)](https://community.n8n.io/t/credential-name-auto-increment-seems-global-for-custom-credentials-but-per-person-for-some-built-ins-openai/296438) | Holdout | Accept that the auto-generated credential name counter is not configurable or scoped per user/project, and manually rename credentials (e.g. include the project or user name) to avoid the global suffix. |

### n8n Academy courses (5)

**Write:** A course FAQ: which courses are retired and what replaced them, how the progress check reads your unique ID, what passing Level 2 requires, and the Loop Over Items 'done' output. Together with the two badge requests under 'always need a person', the course accounts for 7 questions.

| Question | Set | The fix that worked |
|---|---|---|
| [Level 2 – "Getting data from the warehouse" still showing ❌ after completing workflow](https://community.n8n.io/t/level-2-getting-data-from-the-warehouse-still-showing-after-completing-workflow/291081) | Holdout | Make sure the unique ID is set exactly in the workflow's Set node and re-execute the workflow so the HTTP Request node reports progress to the course tracker successfully. |
| [ABCorp's old data warehouse](https://community.n8n.io/t/abcorps-old-data-warehouse/311932) | Holdout | Stop waiting for the welcome email: the Level 1 course (with the ABCorp data warehouse exercise) has been retired, so switch to the replacement n8n Academy beginner course N8N101, Essentials: Your First Workflows, whose exercises use built-in practice APIs. |
| [Level 1 Certification Badge Missing](https://community.n8n.io/t/level-1-certification-badge-missing/279823) | Holdout | Retake the Level 1 certification test and enter the correct community username so the badge is granted and synced to the community profile. |
| [Level 2 - Workflow 3 - Encountering error messaage](https://community.n8n.io/t/level-2-workflow-3-encountering-error-messaage/250592) | Holdout | Skip sending the message to the course Discord channel: verifying with the unique ID and the link from the questionnaire email (a 14/15 score) is enough to pass the course level. |
| [Level 2 course - loop behavior](https://community.n8n.io/t/level-2-course-loop-behavior/295581) | Holdout | Connect a node (e.g., No Operation) to the Loop Over Items node's 'done' output (or otherwise give the loop branch an output), so the loop runs through all batches instead of stopping after the first one. |

### Code node and expressions in 2.x (5)

**Write:** A 2.x Code node page: fetch isn't in the sandbox (use this.helpers.httpRequest), $('Node') references can hang the task runner, typeVersion 2 is needed for Python when creating nodes by API, plus two expression traps ($('...').first() inside pagination, String vs Array in Edit Fields).

| Question | Set | The fix that worked |
|---|---|---|
| [Code nodes freeze](https://community.n8n.io/t/code-nodes-freeze/306079) | Holdout | Avoid using $('Node') / $node['Node'] / $items() references inside the Code nodes (e.g. add a Merge node before the Code node and read $input.all(), or resolve values with expressions in a Set or HTTP Request node) so the task runner doesn't hang requesting the full workflow when an AI Agent with memory/tool sub-nodes is present. |
| [Code Node fetch is not defined Error When Calling External API](https://community.n8n.io/t/code-node-fetch-is-not-defined-error-when-calling-external-api/288365) | Holdout | Replace fetch with the HTTP Request node, or inside the Code node call this.helpers.httpRequest({method, url, json: true}), because fetch is not available in the Code node sandbox. |
| [Unexpected behavior for the "Code" node](https://community.n8n.io/t/unexpected-behavior-for-the-code-node/275504) | Test | Set the Code node's typeVersion to 2 in the workflow JSON sent through the API, because version 1 of the node does not support the Python language option and shows both editors. |
| [Can't get pagination to run with API call to Atlassian Confluence cloud](https://community.n8n.io/t/cant-get-pagination-to-run-with-api-call-to-atlassian-confluence-cloud/309257) | Practice | In the pagination nextURL expression, use $('Set API base URL').first() instead of .item (which fails with 'Missing sourceData' in the pagination context), together with a first-pass guard so the URL is built from the base URL plus _links.next when present and the initial versions path otherwise. |
| [How to extract json string in text file?](https://community.n8n.io/t/how-to-extract-json-string-in-text-file/273323) | Test | In the Edit Fields (Set) node, change the type of the 'data' field from String to Array so the parsed JSON array is kept as real data instead of being coerced to a string ('[object Object]'), and remove the stray leading '=' before the expression. |

### Self-hosting, versions and queue mode (5)

**Write:** A self-hosting checklist: workers must run the main instance's image and config, which version introduced which feature (Chat Hub needs 2.1.0), repairing missing owner scope rows, debugging a schedule that leaves no execution, and the browser extension's localhost requirement.

| Question | Set | The fix that worked |
|---|---|---|
| [Form Trigger fails in queue mode - Cannot read properties of undefined (reading 'execute')](https://community.n8n.io/t/form-trigger-fails-in-queue-mode-cannot-read-properties-of-undefined-reading-execute/297754) | Holdout | Make the worker run the same n8n image/version and the same configuration (encryption key, DB and Redis settings) as the main instance, with the container command set to `worker`, and redeploy both so the worker can load the node type it is asked to execute. |
| [Chat hub missing](https://community.n8n.io/t/chat-hub-missing/271048) | Practice | Upgrade the self-hosted n8n instance from v2.0.3 to at least v2.1.0, since Chat Hub does not exist in earlier versions and no env vars are needed to enable it. |
| [Unable to create/edit any workflows](https://community.n8n.io/t/unable-to-create-edit-any-workflows/312214) | Holdout | Query the user and role_scope tables in Postgres to confirm the user's roleSlug is global:owner, then insert the missing owner scope rows (found by comparing the scope table against role_scope for global:owner), because nothing reconciles role_scope at boot. |
| [Some n8n workflows have no execution history](https://community.n8n.io/t/some-n8n-workflows-have-no-execution-history/297176) | Holdout | Set N8N_LOG_LEVEL=debug and watch the n8n logs at the scheduled time to see whether the trigger fires and an execution row is saved, then check that the workflows are Active and that pruning is not trimming runs. |
| ["[my instance url] it isn't a valid n8n instance."](https://community.n8n.io/t/my-instance-url-it-isnt-a-valid-n8n-instance/309050) | Test | Open the n8n editor via localhost (e.g., an SSH tunnel to 127.0.0.1:5678) so the relay URL hostname passes the browser extension's hardcoded allowlist, then start Connect Browser Use from the Assistant's Connections panel. |

### Node behavior: branches, HTTP methods, sessions (5)

**Write:** A 'how execution really flows' page: branches run in sequence (batch items to run requests in parallel), an extra incoming connection runs a node twice, null values break the LDAP node, the HTTP Request node drops the body on REPORT, and all items of one node execution share one database session.

| Question | Set | The fix that worked |
|---|---|---|
| [Branches don't execute asynchrousnously?](https://community.n8n.io/t/branches-dont-execute-asynchrousnously/306794) | Test | Build the three LLM requests as separate items in a Code node and send them through a single HTTP Request node with Options → Batching → Items per Batch set to 3, so the requests go out in parallel instead of sequential branches. |
| [Workflow executes but says error on last step (it works)](https://community.n8n.io/t/workflow-executes-but-says-error-on-last-step-it-works/254722) | Test | Remove the extra incoming connection (likely the direct one from the AI node) to the HTTP Request node, so it runs only once with the correct input data that includes media[0].source_url. |
| [N8n LDAP Update Node Bug: undefined/null values cause "argument must be a string (was: object)" error (v2.13.4)](https://community.n8n.io/t/n8n-ldap-update-node-bug-undefined-null-values-cause-argument-must-be-a-string-was-object-error-v2-13-4/287340) | Test | Do not pass undefined/null to the LDAP Update node's department attribute; branch the logic before the node (e.g. IF/Switch or separate LDAP nodes per action) so department is only included with a real string value when replacing, and omitted when skipping. |
| [Issues with sending report http request to caldav api](https://community.n8n.io/t/issues-with-sending-report-http-request-to-caldav-api/268997) | Test | Bypass the HTTP Request node, which drops the body for the REPORT method, by making the REPORT request with the XML body, Depth header and auth directly from a Code node using fetch (or the https module). |
| [Is there a way to set Snowflake QUERY_TAG from n8n?](https://community.n8n.io/t/is-there-a-way-to-set-snowflake-query-tag-from-n8n/310720) | Holdout | Send ALTER SESSION SET QUERY_TAG as the first input item and the real query as a later item into a single Snowflake node (Query set to {{ $json.sql }}), because all items of one node execution share one connection/session. |

### Triggers and webhook registration (4)

**Write:** A trigger registration page: re-activating a workflow re-registers its webhook (Meta subscriptions go stale), pasted trigger nodes share a webhook ID, two Lead Ads forms need the same Facebook app, and a trigger with an empty credential fails to publish.

| Question | Set | The fix that worked |
|---|---|---|
| [Prod N8N WhatsApp Trigger not working](https://community.n8n.io/t/prod-n8n-whatsapp-trigger-not-working/290067) | Holdout | Re-activate the WhatsApp workflow (unpublish/republish, or automate it via a scheduled workflow calling the n8n public API /workflows/{id}/activate with an X-N8N-API-KEY) so n8n re-registers the webhook subscription with Meta. |
| [Shopify trigger error](https://community.n8n.io/t/shopify-trigger-error/299450) | Test | Delete the copy-pasted Shopify Trigger node and add a fresh Shopify Trigger node (not pasted) in each workflow, so each gets its own unique webhook path/ID and the activation conflict clears; use a separate trigger per topic (create/update/delete). |
| [How to have 2 facebook Lead ad trigger nodes in n8n](https://community.n8n.io/t/how-to-have-2-facebook-lead-ad-trigger-nodes-in-n8n/254693) | Test | Configure both Facebook Lead Ads Trigger nodes (one per form) with credentials from the same Facebook app, because separate apps do not both deliver webhook events to n8n. |
| [Unable to publish workflow](https://community.n8n.io/t/unable-to-publish-workflow/270419) | Test | Re-attach the Zendesk API credential to the Zendesk Trigger node (its credentials object was empty), so that publishing registers the webhook with Zendesk using valid authentication instead of a blank payload that returns 400 Bad Request. |

### Community, creators and accounts (4)

**Write:** Short answers that belong in a creators and community FAQ: a creator page goes live after templates are approved, how verification treats a rebuilt node with no runtime dependencies, personal email is fine for sign-up, and what a good forum question includes.

| Question | Set | The fix that worked |
|---|---|---|
| [How to activate my n8n creator page after registering as a creator?](https://community.n8n.io/t/how-to-activate-my-n8n-creator-page-after-registering-as-a-creator/274571) | Test | Submit workflow templates to the n8n template library and get them approved (reportedly around 3), after which the creator page goes live automatically. |
| [Verification question: existing node has a runtime dep that blocks it — does a fresh package qualify?](https://community.n8n.io/t/verification-question-existing-node-has-a-runtime-dep-that-blocks-it-does-a-fresh-package-qualify/300429) | Holdout | Publish a new, independently built community node package under your own npm name with zero runtime dependencies (not a PR to the existing n8n-nodes-attio), and explain in the verification submission that it is an independent rebuild because the existing node's runtime dependency makes it unverifiable. |
| [Email addresse](https://community.n8n.io/t/email-addresse/292397) | Test | Use a personal email address to sign up, since n8n does not restrict sign-up to company emails (only some external services may require a corporate email). |
| [A Guide To the forum](https://community.n8n.io/t/a-guide-to-the-forum/310250) | Practice | When posting a question, include the workflow JSON (copy the failing nodes with Ctrl+C and paste them in a code block), the n8n version and setup from Help > About, and the full error text from the node's JSON output Details section. (forum had the fix earlier) |

### Binary data and email attachments (3)

**Write:** An attachments recipe: carry binary from the trigger to the send node, give each binary property a unique name to send several in one email, and fetch large attachments one at a time to stay inside Cloud memory.

| Question | Set | The fix that worked |
|---|---|---|
| [Email attachments not sending via SMTP node in n8n 2.3.0 (self-hosted)](https://community.n8n.io/t/email-attachments-not-sending-via-smtp-node-in-n8n-2-3-0-self-hosted/309749) | Test | Re-attach the IMAP trigger's binary data to the item just before the Send email node (e.g. with a Code node returning json plus binary from the trigger), then set the Attachments option to the binary property names on that item, e.g. {{ Object.keys($binary).join(',') }}. (forum had the fix earlier) |
| [Multiple Attachments Mail via outlook](https://community.n8n.io/t/multiple-attachments-mail-via-outlook/255738) | Test | Rename each item's binary field to a unique name (e.g. data1, data2) with a Set/Edit Fields node, merge the items into a single item, then list each binary property name as an attachment in one Outlook node so only one email is sent. |
| [Workspace offline (503) – Urgent - memory limit hit during first test?](https://community.n8n.io/t/workspace-offline-503-urgent-memory-limit-hit-during-first-test/296744) | Test | Turn off downloadAttachments on the Gmail trigger so it returns only metadata, then fetch each PDF one at a time with a Gmail 'Get a Message Attachment' node inside a SplitInBatches loop (batch size 1) so only one attachment is held in memory. |

### Plans, limits and migration (2)

**Write:** Two facts customers look for before buying: current Cloud execution limits (the old 5-minute Starter limit is gone) and that there's no Zapier importer, with a staged migration plan instead.

| Question | Set | The fix that worked |
|---|---|---|
| [Are there workflow execution time limits?](https://community.n8n.io/t/are-there-workflow-execution-time-limits/276736) | Test | Recognize that the old 5-minute Starter execution limit is outdated and that n8n Cloud no longer enforces a short per-workflow timeout, so long-running workflows are allowed, with the current limits described in the Cloud docs. |
| [Has anybody migrated workflows from zapier to n8n](https://community.n8n.io/t/has-anybody-migrated-workflows-from-zapier-to-n8n/307984) | Practice | Rebuild each Zap manually as an n8n workflow (trigger, conditions, actions), migrating incrementally starting with simple Zaps and running Zapier in parallel to verify results, since there is no automatic import. |

## Known issues a bot should be told about (15)

The fix is "it's a bug in this version" plus a workaround or the version that fixes it. Docs can't say that in time; a known-issues feed can.

### Node bugs with a workaround (9)

**Tell the bot:** Give the bot the open, confirmed node bugs with their workaround (use the HTTP Request node, pin the node version, turn off Always Output Data), so the customer gets the workaround and the route in one reply.

| Question | Set | The fix that worked |
|---|---|---|
| [DeepSeek Chat Model got issues with reasoning_content](https://community.n8n.io/t/deepseek-chat-model-got-issues-with-reasoning-content/298570) | Practice | Replace the built-in DeepSeek Chat Model with the community node n8n-nodes-deepseek-v4 and disable Thinking Mode there, because n8n's built-in node does not pass reasoning_content back to the API (a known issue awaiting a fix). |
| [Switch node always output/continue issue](https://community.n8n.io/t/switch-node-always-output-continue-issue/274129) | Practice | Turn off 'Always Output Data' on the Switch node, because it wrongly sends the empty item through the first output (a known bug tracked in GitHub issue #17504), and handle empty branches separately, for example with a No Operation node after each output. |
| [Mailjet Credentials / Sandbox setting gets synced when working with environments](https://community.n8n.io/t/mailjet-credentials-sandbox-setting-gets-synced-when-working-with-environments/273951) | Test | Treat the synced Mailjet sandbox credential setting as an n8n bug and work around it by keeping sandbox vs live out of the credential, for example by using an HTTP Request node with an environment-variable base URL or separate credentials per environment, and file a GitHub bug. |
| [AI Agent stop when tool fail](https://community.n8n.io/t/ai-agent-stop-when-tool-fail/297687) | Test | Downgrade the AI Agent node's typeVersion from 3.1 to 2.2 by editing the node JSON, as a workaround for a v3.1 bug where a failing or empty tool result stops the agent. (forum had the fix earlier) |
| [Webhook Test Mode 500 – Cannot read properties of undefined (reading 'name') (Cloud 2.6.3)](https://community.n8n.io/t/webhook-test-mode-500-cannot-read-properties-of-undefined-reading-name-cloud-2-6-3/264833) | Test | Open the Webhook node and fix its Respond setting: either add and connect a Respond to Webhook node, or change 'Respond' to 'Immediately' or 'When Last Node Finishes' so the test-mode response-mode check no longer hits a missing child node. |
| [Invalid URL error on Discord node](https://community.n8n.io/t/invalid-url-error-on-discord-node/307158) | Test | Replace the Discord node's webhook send with an HTTP Request node that POSTs to the Discord webhook URL, since the Discord node's webhook path has a bug (tracked as NODE-5739) that no setting fixes. |
| [Azure Ai Search Vector Store: Hybrid Search (Keyword Search) not working](https://community.n8n.io/t/azure-ai-search-vector-store-hybrid-search-keyword-search-not-working/264152) | Holdout | Bypass the buggy native Azure AI Search Vector Store node by calling the Azure AI Search REST API directly with an HTTP Request node (optionally wrapped in a sub-workflow), and update n8n once a fix is released. |
| [MCP get_workflow_details returns empty workflow.tags for tagged workflows](https://community.n8n.io/t/mcp-get-workflow-details-returns-empty-workflow-tags-for-tagged-workflows/298353) | Holdout | Bypass the MCP get_workflow_details tool, which returns an empty tags array because of a likely MCP implementation gap, and fetch the workflow with the public REST API (GET /api/v1/workflows/{id}) using an API key to get the tags. |
| [@n8n/scan-community-package failing for cred filename](https://community.n8n.io/t/n8n-scan-community-package-failing-for-cred-filename/304343) | Test | Run the scanner from the beta tag (npx @n8n/scan-community-package@beta @ambriel-io/n8n-nodes-ambriel) because the tagged release had a bug in the cred-filename-against-convention lint check, and the beta carries the fixed lints. |

### Version regressions with a known fix or safe version (6)

**Tell the bot:** Give the bot each release's fixed-issue notes with version numbers, so it can say "2.15.0 has this bug; 2.17 fixes it" instead of guessing.

| Question | Set | The fix that worked |
|---|---|---|
| [All Google Related Node Error: dummy.stack.replace is not a function (Self-hosted n8n)](https://community.n8n.io/t/all-google-related-node-error-dummy-stack-replace-is-not-a-function-self-hosted-n8n/286540) | Test | Upgrade n8n from 2.15.0 to a newer release (the accepted answer says 2.17+), where the error-handling bug behind 'dummy.stack.replace is not a function' was reportedly fixed. |
| [CMD / Powershell-Fenster via Execute Command Node öffnen sich nun sichtbar](https://community.n8n.io/t/cmd-powershell-fenster-via-execute-command-node-offnen-sich-nun-sichtbar/302503) | Test | Roll back n8n to the version installed before the update (npm install -g n8n@<previous-version>), because 2.29.7 introduced a regression that makes the Execute Command shell window visible on Windows. |
| [Airtable node resource locator fails with "No bridge acquired for this context" — Cloud 1.123.69](https://community.n8n.io/t/airtable-node-resource-locator-fails-with-no-bridge-acquired-for-this-context-cloud-1-123-69/306956) | Test | Upgrade the n8n Cloud workspace from 1.123.69 to a newer version in which the 'No bridge acquired' expression-engine bug is fixed, by changing the version in the Cloud dashboard (Manage > Workspace > Updates & maintenance). |
| [Instance-level MCP settings not persisting via UI (self-hosted Docker)](https://community.n8n.io/t/instance-level-mcp-settings-not-persisting-via-ui-self-hosted-docker/268806) | Test | Upgrade n8n from 2.8.3 to version 2.9.0 or later, which includes the fix for the MCP toggle in workflow settings not persisting (PR #25630). |
| [I can't find the feature to focus a single column in node input/output any more - was it removed?](https://community.n8n.io/t/i-cant-find-the-feature-to-focus-a-single-column-in-node-input-output-any-more-was-it-removed/271805) | Practice | Report the missing column-focus button in Table view (n8n@2.9.3) as a regression on the n8n GitHub repo, and use JSON view with Ctrl+F as a temporary workaround. |
| [N8n AI Agent PostgreSQL Tool shows invalid/missing schema error (query input not working)](https://community.n8n.io/t/n8n-ai-agent-postgresql-tool-shows-invalid-missing-schema-error-query-input-not-working/299774) | Holdout | Work around the n8n 2.26.x bug that builds an invalid tool schema ('must be type object, got None') by either dropping the agent tool (generate SQL with a Message a Model node and run it in a regular Postgres node) or downgrading to n8n 2.15. |

## Questions that always need a person (7)

Only n8n staff can act: a badge, an account, a review queue, a quote. The bot's job is one right route, fast.

### n8n Academy badges (2)

**Route:** Route: the course admin, with the unique ID and community username.

| Question | Set | The fix that worked |
|---|---|---|
| [The badge :)](https://community.n8n.io/t/the-badge/257991) | Test | An n8n staff member with admin access to the course platform must assign the missing Level 1 course badge to the user's account, after cleaning up duplicate accounts. |
| [Insignia curso level 1](https://community.n8n.io/t/insignia-curso-level-1/264436) | Holdout | An n8n team member or course admin must verify the user's course completion and unique ID in the course/badge system and award the forum badge, which the customer cannot do themselves. |

### Creator Hub and community-node review (2)

**Route:** Route: creators@n8n.io for Creator Hub account changes; help@n8n.io for the review queue.

| Question | Set | The fix that worked |
|---|---|---|
| [N8n Creators Hub Email Change](https://community.n8n.io/t/n8n-creators-hub-email-change/299944) | Practice | Email the n8n team at creators@n8n.io with the current account details and the new email address, because n8n staff must change the Creator Hub email since there is no self-service setting. |
| [How can I update an under-review community node to use the latest npm build?](https://community.n8n.io/t/how-can-i-update-an-under-review-community-node-to-use-the-latest-npm-build/290662) | Holdout | Email help@n8n.io asking n8n staff to switch the Creator Portal review for both packages from the submitted versions (0.1.8 and 0.1.9) to the latest npm version 0.2.0. |

### Pricing and forum structure (2)

**Route:** Route: sales for an enterprise quote; the Feedback category for a new forum section.

| Question | Set | The fix that worked |
|---|---|---|
| [Enterprise plan costs](https://community.n8n.io/t/enterprise-plan-costs/297408) | Holdout | Contact n8n sales for a custom enterprise quote, since enterprise pricing is not published; alternatively self-host Community Edition if enterprise features are not needed. |
| [How to create a language section in Tutorials](https://community.n8n.io/t/how-to-create-a-language-section-in-tutorials/278295) | Holdout | Community members cannot create new forum category sections themselves, so the user should open a topic in the Feedback category so the n8n team can decide on adding a Polish Tutorials section, and meanwhile post in an existing section. |

### Cloud workspace down (1)

**Route:** Route: a support ticket with the workspace ID and when the loop started; say plainly that only n8n can repair it.

| Question | Set | The fix that worked |
|---|---|---|
| [Cloud Instance 503 Loop - Down for 12+ Hours](https://community.n8n.io/t/cloud-instance-503-loop-down-for-12-hours/258295) | Test | n8n staff/engineering must repair the crashing Cloud workspace backend (e.g., failed migration or database problem), which the customer cannot do themselves; the customer should keep the support ticket open and provide workspace ID and the time the loop started. |

## Not a docs gap, but the largest theme tagged: making a workflow run exactly once (13 of 74)

General engineering covers these (idempotency keys, unique constraints, row locks, ordering). A single n8n patterns page showing each one with n8n nodes would still save the forum a lot of answers.

| Question | Set | The fix that worked |
|---|---|---|
| [Partial failures when an n8n workflow calls multiple APIs](https://community.n8n.io/t/partial-failures-when-an-n8n-workflow-calls-multiple-apis/310338) | Practice | Generate a stable per-step idempotency key (e.g. order-123-payment), check the external API for the existing result before retrying, and resend the request with the same key only if the operation did not already complete. |
| [Way to Prevent Duplicate Workflow Executions from Multiple Webhook Retries](https://community.n8n.io/t/way-to-prevent-duplicate-workflow-executions-from-multiple-webhook-retries/295919) | Practice | Insert the event_id into a database table with a UNIQUE constraint (INSERT ... ON CONFLICT DO NOTHING) before processing, and only continue the workflow if the insert succeeded, otherwise skip it. |
| [Handle Failed n8n Workflows Without Losing Data](https://community.n8n.io/t/handle-failed-n8n-workflows-without-losing-data/306976) | Practice | Persist a job record (job_id, current_step, status, retry_count) to external storage after each important step, and make external actions idempotent so a retry or recovery workflow resumes from the last successful step instead of rerunning completed steps. |
| [Handle out-of-order webhook events](https://community.n8n.io/t/handle-out-of-order-webhook-events/310057) | Test | Add a version (or sequence/timestamp) column and make the UPDATE conditional with WHERE id = $1 AND version < $3, setting version = $3, so PostgreSQL atomically rejects older events. |
| [Exactly-once processing failure in paginated](https://community.n8n.io/t/exactly-once-processing-failure-in-paginated/271354) | Test | Store the pagination cursor and a lock flag in a database table (not workflow static data), acquire the lock before each run, write records idempotently with ON CONFLICT DO NOTHING, and advance the cursor only after the page is successfully written. |
| [Prevent n8n workflows from processing the same job twice after a worker failure](https://community.n8n.io/t/prevent-n8n-workflows-from-processing-the-same-job-twice-after-a-worker-failure/307866) | Test | Claim jobs atomically in PostgreSQL with SELECT ... FOR UPDATE SKIP LOCKED inside an UPDATE, and guard every later update with a lease timeout and a worker_id condition (WHERE id = $1 AND status = 'processing' AND worker_id = $2) so stale workers cannot overwrite reclaimed jobs. |
| [N8n Workflow Fails to Resume Safely After Partial Execution (Idempotency & Checkpointing Issue)](https://community.n8n.io/t/n8n-workflow-fails-to-resume-safely-after-partial-execution-idempotency-checkpointing-issue/293072) | Test | Persist the last successfully processed page number in an external database, read it at the start of each run to resume from the next page, and update it only after that page has been processed and stored. |
| [Handling Exactly Once Processing with Webhooks](https://community.n8n.io/t/handling-exactly-once-processing-with-webhooks/294568) | Holdout | Store each event_id in a database table with a UNIQUE/PRIMARY KEY constraint and insert it before processing with ON CONFLICT DO NOTHING, so only the first insert proceeds and duplicate events are skipped. |
| [Workflow Randomly Reprocessing Old Queue Jobs After Worker Restart](https://community.n8n.io/t/workflow-randomly-reprocessing-old-queue-jobs-after-worker-restart/296374) | Holdout | Make processing idempotent by checking for an already-processed status before running and enforcing database-level deduplication (unique keys / ON CONFLICT DO NOTHING), because queue mode can re-run unacknowledged jobs after a worker crash or restart. |
| [Partial Failures Between n8n and PostgreSQL](https://community.n8n.io/t/partial-failures-between-n8n-and-postgresql/313213) | Holdout | Make the workflow state-driven and idempotent: store an idempotency key per operation with a PostgreSQL unique constraint (INSERT ... ON CONFLICT DO NOTHING) and status values (pending/processing/completed), so a recovery workflow can check whether the API call already happened before retrying. |
| [How to prevent duplicate emails in AI Agent workflow when ready_to_email stays true](https://community.n8n.io/t/how-to-prevent-duplicate-emails-in-ai-agent-workflow-when-ready-to-email-stays-true/297603) | Holdout | Store the 'email sent' flag outside the AI in a Postgres table keyed by Telegram chat ID, look it up before the IF node, and send the email only when the AI says ready AND the database says not yet sent, then update the row to true after sending. |
| [Duplicate WhatsApp Messages](https://community.n8n.io/t/duplicate-whatsapp-messages/309667) | Holdout | Deduplicate by WhatsApp message_id: store it with a 'processing' status in a persistent store (e.g. a database or data table) before processing and sending the reply, check for an existing entry when a webhook arrives, and update it to 'completed' afterward. |
| [Way to Prevent Message Ordering Issues in a High-Volume WhatsApp Automation System](https://community.n8n.io/t/way-to-prevent-message-ordering-issues-in-a-high-volume-whatsapp-automation-system/297742) | Holdout | Partition or queue incoming messages by user_id (optionally with a per-user Redis lock) so that all messages for one user are processed serially by a single worker while different users run in parallel. |

## What the forum already knew

For the 37 practice and test questions on the n8n-know-how and known-issue side, we searched a harvest of 2,739 solved threads, keeping for each question only answers posted before it (about 2,070 per question). The fix was there for 3 of 37. Most gaps are new when they reach the forum, so a bot fed past answers mostly can't close them; articles and a known-issues feed can.

## How this was built, and its limits

- Labels: two labelers (Claude Sonnet 5.5 and Gemini 3.8 Flash) each searched the docs three ways and chose a category; a blind tie-breaker (Muse Spark 1.3) settled disagreements; Jonathan Marx read every disagreement that crossed the line between answerable and needs-a-human. Rules: `rubric/LABELING-v2.md`.
- The docs are pinned to one commit (`data/docs_commit.txt`); the questions span January to September 2026.
- People post on a forum after the docs failed them, so forum questions overstate the gap compared with a normal support queue.
- Themes were assigned by hand from the fix summaries (`data/docs_gap_themes.json`); `audit/docsgap.py` checks that every needs-a-human question appears exactly once.
