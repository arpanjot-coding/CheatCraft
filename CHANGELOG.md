# CheatCraft 0.4.0

- Rename the project and portable executables to CheatCraft.
- Remove test-session controls, example values and sample-process operations from the product. Keep the controlled fixture only in the test suite.
- Add explicit detach, snapshot deletion and watch-field prefilling.
- Prevent shutdown from starting queued mutations or interrupting active export writes.
- Use unique temporary files for atomic exports; preserve unrelated files and the original export if replacement fails.
- Fix sorting precision for large integers and identify unreadable snapshot baselines.
- Separate visual layout, UI state, storage and test fixtures; lint and format the source.
- Include the responsive five-workspace redesign, background watch reads, MCP result synchronization, page-read fallback and strict JSON serialization introduced during the 0.3 development cycle.
- Add detailed documentation, source contribution guidance, a Windows CI template and a two-executable portable release build.

## Earlier 0.2 development changes

- Refine candidates by changed, unchanged, increased, or decreased values, using observations from the last successful search/refinement.
- Cancel searches/refinements from the desktop, Escape key, or MCP. Cancellation preserves the previous candidate set, type, and comparison baseline.
- Read scan progress during an active MCP scan through a concurrent authenticated bridge. Connections are capped at eight concurrent clients.
- Filter processes by name or PID. Keyboard shortcuts: Ctrl+F for the filter and Ctrl+R to refresh.
- Show readable scan duration, bytes visited, match counts, incomplete results and skipped bytes.
- Preserve watch selection and scroll position during refresh.
- Prevent multiple current-version desktops from replacing the same MCP session configuration.
- Save startup failures to a local error log with an explanatory dialog.
- Reduce per-read process-discovery overhead by checking the existing process handle for termination.

This release improves normal Windows diagnostics. It does not establish feature parity or performance superiority over Cheat Engine. Tests cover the controlled target; broad game compatibility and large-process performance remain to be measured.
