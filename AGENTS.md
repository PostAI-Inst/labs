# Post-AI Institute Labs maintenance

This repository is the public collection of Post-AI Institute's research prototypes and games. The user's authorized destination is `PostAI-Inst/labs`, maintained using the `NirViaje` identity. Verify that identity and repository before remote changes. Preserve other accounts and repositories.

## Catalogue

- `projects.json` is the only catalogue source. Generate `index.html` with `python3 scripts/build_index.py`; do not hand-edit its project cards. If generation runs in a materialized preview tree, copy its regenerated `index.html` back to the repository checkout before committing it with `projects.json` and the changed project files.
- Keep stable project IDs and paths. New runnable projects belong in `projects/<slug>/`. Preserve their supporting files and original research dates.
- Use relative paths that work beneath `/labs/`. Keep local browser storage keys distinct between unrelated projects.
- Register secondary HTML pages with `auxiliary_entries`, or link them from the indexed project. A different filename must not hide a new project from the index audit.
- Keep materially different models and game prototypes distinct. Group the same model's older interfaces under a version archive, with differences explained.
- Mark optional backend, hardware or browser requirements in `notes`. An inaccessible source is an unresolved check, not evidence that no project exists.

## Publication and evidence

- The user requested a public GitHub Pages collection and continuing discovery of relevant new projects. Routine additions, fixes and catalogue updates within this scope are authorized.
- Publish only the intended research prototype and its required assets. Keep private conversation transcripts, cooperation contracts, unpublished evaluation questions, credentials and internal source registries outside this public repository.
- Preserve original attribution and licence information. Do not assign a new blanket open-source licence to third-party or previously unlicensed materials.
- Validate the checkout's homepage with `python3 scripts/build_index.py --check`. Run `scripts/audit.py` from a complete materialized tree, since a checkout may contain only overrides and cannot by itself validate baseline project assets. Check the changed project's key browser interaction when possible; describe actual verification limits accurately.
- The Pages workflow deploys `main`; verify the resulting deployment before reporting a project as live.

## Continuing discovery

The scheduled assistant compares accessible conversations, files, research Pages, Sites and the original `PostAI-Inst/boardgame-lab` with this catalogue. A private source registry records original file identities and versions. Do not copy that registry into this repository.

Repository CI checks internal consistency on changes and weekly. It does not have access to ChatGPT conversations or files. Record concrete new projects, revisions, broken links and unresolved sources; avoid empty duplicate updates.

## Source layout

The complete initial collection is stored as the named source ZIP in this repository’s Release. `source-archive.json` pins its size and SHA-256. `main` contains the catalogue, maintenance scripts and incremental overrides. Run `scripts/materialize.py --output <empty-directory-outside-checkout>` to obtain the full tree before checking or editing; choose a new empty directory on subsequent runs.

For a baseline-only file, copy the file from the materialized tree into the same relative path in the checkout before editing, or copy all intended changes back afterwards. Editing a temporary materialized tree alone does not update the repository. Commit the changed files and the regenerated `index.html` together with `projects.json`; preserve the pinned baseline.

To remove a baseline file from the final site, add its exact repository-relative path to `source-archive.json` → `exclude_paths` and update catalogue entries and references. Removing only a checkout override restores the baseline copy. Exclusions apply after all overlays and therefore also remove overrides at the same path. Never use an empty path or `.` as an exclusion.

The CI workflow only reads sources and deploys Pages, and has no repository write permission. Do not add repository write permission or a commit/push step to work around a failed publication or validation.
