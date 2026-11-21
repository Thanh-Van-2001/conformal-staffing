\cnt{date}

The Editors\
IISE Transactions on Healthcare Systems Engineering

Dear Editors,

Please consider the enclosed manuscript, "How many ambulances for nine good days in ten? A conformal staffing rule tested in seven EMS service areas", for publication as an Original Research Article in *IISE Transactions on Healthcare Systems Engineering*. The manuscript is prepared for double-anonymous review: the anonymous PDF and its LaTeX sources carry no author details, which are on the separate title page. A STRESS-DES reporting checklist for simulation studies and one supplementary table are uploaded as supplemental material.

The paper is a healthcare systems engineering study of a capacity decision that every emergency medical service (EMS) agency makes: how many ambulances to staff in each hour of the day. It combines queueing-based staffing (square-root and Erlang-C rules), trace-driven discrete-event simulation of the recorded calls and distribution-free statistical calibration, and evaluates them out of sample on \res{totalCalls} public dispatch records from seven New York City and San Francisco service areas. We believe it fits the journal's readership in healthcare operations, capacity planning and data-driven decision making under uncertainty.

Agencies' staffing rules aim at an average delay and do not say how often a whole day will go badly. Recent EMS studies put prediction intervals, including conformal intervals, around forecasts of call volume or response time, but none turns them into a staffing plan with a day-level promise. The manuscript calibrates the staffing decision itself: for each recent day, simulation finds the smallest safety margin that would have kept that day within the service target, and the plan uses a rank of these margins chosen so that, under exchangeability, nine days in ten meet the target. The method is a special case of conformal risk control and we claim no new theory; what is new is calibrating the staffing decision on real dispatch data under demand drift, with an analysis plan fixed in advance and rolling out-of-sample evaluation.

Over more than three years of rolling planning, the rule met the target on \res{covSCDMinPct} to \res{covSCDMaxPct} percent of days. It used \res{premSCDMin} to \res{premSCDMax} percent more unit-hours than a hindsight benchmark and \res{extraMOLMin} to \res{extraMOLMax} percent more than the Erlang-C rule MOL; the Erlang-C rules in common use met the day-level target on only \res{covSIPPMinPct} to \res{covMOLMaxPct} percent of days. Calibrating the demand forecast instead of the staffing decision cost \res{acaOverSCDMin} to \res{acaOverSCDMax} percent more unit-hours.

The manuscript reports its negative pre-specified results plainly. The validity criterion failed (\res{hOneSeedMin} to \res{hOneSeedMax} of 7 areas passed; 6 were required) because coverage fell when demand grew after calibration, and the hypothesis that the in-sample rule is optimistic was not supported. Exploratory comparisons with current drift-adaptive conformal methods are labeled as such: recency-weighted calibration reached \res{xWCPcovMinPct} to \res{xWCPcovMaxPct} percent of days at a small extra cost, while a trend adjustment did not help. The outcome is the availability of a free unit in a single pool, not response time, and the limitations section says so.

The manuscript is original, has not been published elsewhere and is not under consideration by any other journal. The data were prepared for an earlier study by the same author on a different question (arrival models for cost-optimal staffing), which is under review at another journal; the overlap is limited to the data preparation and is disclosed in the manuscript in anonymous form. The analysis plan and its four amendments are under version control; the code, the simulator and the results are available on request during review and will be made public upon acceptance. The use of generative AI tools is disclosed in the manuscript. The author declares no competing interests and received no specific funding.

Sincerely,

Thanh Van Nguyen\
Tsinghua Shenzhen International Graduate School, Tsinghua University, Shenzhen, China\
felicenguyen2001@gmail.com
