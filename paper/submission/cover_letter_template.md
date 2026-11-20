\res{coverDate}

The Editor\
Prehospital Emergency Care

Dear Editor,

Please consider the enclosed manuscript, "How many ambulances for nine good days in ten? A conformal staffing rule tested in seven EMS service areas", for publication as an original research article. A STRESS-DES reporting checklist for simulation studies is uploaded with it.

EMS agencies set hourly ambulance staffing with queueing rules that aim at an average delay. They do not say how often a whole day will go badly. Recent EMS studies put prediction intervals, including conformal intervals, around forecasts of call volume or response time, but none turns them into a staffing plan with a day-level promise. The manuscript calibrates the staffing decision itself: for each recent day, simulation of the recorded calls finds the smallest safety margin that would have kept that day within the service target, and the plan uses a rank of these margins chosen so that, in principle, nine days in ten meet the target. To our knowledge this is the first test of such a rule on real dispatch data, here \res{totalCalls} public records from seven New York City and San Francisco service areas, under a plan committed before any staffing computation.

Over more than three years of rolling out-of-sample planning, the rule met the target on \res{covSCDMinPct} to \res{covSCDMaxPct} percent of days. It used \res{premSCDMin} to \res{premSCDMax} percent more unit-hours than a hindsight benchmark and \res{extraMOLMin} to \res{extraMOLMax} percent more than the common Erlang-C rule, which met the day-level target on only \res{covSIPPMinPct} to \res{covMOLMaxPct} percent of days. Calibrating the demand forecast instead of the staffing decision cost \res{acaOverSCDMin} to \res{acaOverSCDMax} percent more unit-hours.

The manuscript reports its negative pre-specified results plainly. The validity criterion failed (\res{hOneSeedMin} to \res{hOneSeedMax} of 7 areas passed; 6 were required) because coverage fell when demand grew after calibration, and the hypothesis that the in-sample rule is optimistic was not supported. Exploratory comparisons with current drift-adaptive conformal methods are labelled as such: an adaptive level brought coverage close to nominal, and recency-weighted calibration and quantile tracking from conformal PID control reached about the nominal rate at a small extra cost, while a trend adjustment did not help. A comparison with conformal risk control shows that promising a good average share of delayed calls, rather than few bad days, gives cheaper plans that fail the day-level target far more often. The outcome is the availability of a free unit in a single pool, not response time, and the limitations section says so.

The analysis plan and its four amendments are in version control, and the code and results will be public at https://github.com/Thanh-Van-2001/conformal-staffing.

The manuscript is original, has not been published elsewhere and is not under consideration by another journal. The data were prepared for an earlier study by the same author on a different question, which is under review elsewhere; this is disclosed in the manuscript. The use of generative AI tools is also disclosed in the manuscript. The author declares no competing interests and received no specific funding.

Sincerely,

Thanh Van Nguyen\
Tsinghua Shenzhen International Graduate School, Tsinghua University\
felicenguyen2001@gmail.com
