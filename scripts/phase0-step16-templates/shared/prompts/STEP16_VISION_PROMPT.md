# Step 16 Vision Capability Prompt

**Status:** capability-spike control; incorporated into the experiment contract only after a passing Step 16 audit

All three provider paths receive the same synthetic target, the same image bytes, and the same semantic instructions.
Transport wrappers may differ only where the pinned framework API requires it.

## System instruction

```text
You are performing a bounded capability check for an accessibility workflow.
Use only the supplied synthetic image and page context. Do not infer a real agency, program,
person, location, event, or operational fact. Return only the requested structured object.
```

## User template

```text
PAGE CONTEXT
Title: {{article_title}}
Body: {{article_body_plain}}

IMAGE METADATA
Filename: {{filename}}
MIME type: {{mime_type}}
Dimensions: {{width}} x {{height}}

TASK
Inspect the attached image together with the page context. Return:
- image_purpose: what the synthetic image communicates in this page context
- proposed_alt_text: concise contextual alt text, no more than 250 characters
- context_alignment: one short sentence explaining how the image and supplied page context align

Do not begin the alt text with "image of", "photo of", "picture of", "graphic of", "Here is", or
"Alt text:". Do not repeat the filename. Return no properties beyond the schema.
```

## Tool capability prompt

```text
Use the supplied calculator tool exactly once to calculate 20 * (4 + 3). Return the tool result.
```

The tool check is harmless, read-only, and separate from the image call. It proves that the pinned
provider wrapper can expose a tool-call pathway without implementing Step 17 or mutating Drupal.
