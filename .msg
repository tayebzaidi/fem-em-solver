ANS-4 step 2d: match the AED design (degree 2 at their unknown count), not just a finer mesh

Operator direction: run the XL slot at degree 2 with the matching higher mesh,
to approximate the Ansys setup. Sizing it revealed my previous rung target was
matching the wrong column.

By ANS-5, our degree 2 IS HFSS First Order. AED's First Order run is its
converged one and needed only 0.49-0.60 M tets (3.1-3.8 M unknowns); its
1.28-1.53 M tet figure belongs to the Zero Order design, because order buys
accuracy per tet. So the rung that approximates AED is degree 2 at ~0.5 M
cells (~3.0 M unknowns, ~226 GiB by the TH-11 step 5d measurement of 260.9 GiB
at 3.37 M unknowns) -- far over the ordinary 128 G service and inside 512 G,
which is what the tier is for. Degree 2 on the 1.5 M Zero Order mesh would be
~9.8 M unknowns and ~1.1 TB, past this tier and past anything Ansys ran, and
is explicitly not attempted.

Ladder: 0.015:1 (control, exact cell record) then 0.015:2, 0.0075:2, 0.005:2.
The 0.015:2 rung is a free cross-check -- it must reproduce step 2b's recorded
degree-2 entries before anything is concluded from the finer ones -- and the
three degree-2 rungs give a Richardson h-ladder at the matched order, which is
what an order-matched comparison actually needs.

Code: FEM_EM_ANS4_STEP2_RUNGSPEC takes explicit h:degree rungs, and the stop
rule is now in unknowns (4.5 M, ~400 GiB) rather than cells, since cells mean
different things at different orders and memory tracks unknowns. The dof
estimate uses the 6.4 N ratio AED's own matrix sizes confirmed at 6.34.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01M4CQKWcum9G6UmqdHtunkv
