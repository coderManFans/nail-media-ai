# Task execution
Generate definitions with python -m nail_media.tasks. Enable only configured tasks in runtime/tasks.json.
Supply an input mapping keyed by task ID, e.g. {"task-id":{"adapter":"manifest","file":"examples/manifest.json"}}.
Run python -m nail_media.runner --inputs runtime/inputs.json.
This runner processes authorized local inputs; keyword search, network adapters and recurring scheduling are not yet implemented.
Archive: clone the dedicated data repository locally, verify it is private, review the metadata, then run python -m nail_media.archive --checkout ../nail-media-data --confirm-authorized.
Review git diff and commit/push manually. No automatic publication.
