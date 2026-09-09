ops: an XL window waits for the box

Operator direction: check the shared machine before starting an XL run and
postpone if it is already busy. An XL window holds up to 16 of 36 cores for up
to two hours, so starting one onto somebody else's work is the rudest thing
this project can do -- and nothing was stopping it except my judgement.

bash_guard.py now refuses an XL command when the 1-minute load average leaves
fewer free cores than the window's own rank count plus 4 cores of headroom.
The rank count is parsed from the command, so an 8-rank window is allowed at a
load that postpones a 16-rank one. The denial names the current load, the free
cores, what the window wants, and the figure the load must fall below, so it
reads as "come back at X" rather than "no".

Two deliberate properties, both documented in §5.1 and the docstring: it fails
open, because a guard that cannot read /proc/loadavg must not become the
reason nothing can run; and load average is a decaying mean that cannot
separate our own load from anyone else's, so for a minute or two after one of
our runs ends it will postpone the next one. That is the safe direction.
FEM_EM_XL_IGNORE_LOAD=1 is the operator's escape hatch for exactly that case,
and explicitly not a way past somebody else's work.

Verified across the threshold at 36 cores: allow at load 0.7 and 12.0,
postpone at 16.1 and 25.0, allow at 30.0 with the override, and allow at 20.0
when the window asks for only 8 ranks.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01M4CQKWcum9G6UmqdHtunkv
