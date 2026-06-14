# Plain-English UX Language

EdgeLab should explain conclusions before metrics.

## Doctrine

- Plain English first, technical terms second.
- No brokerage or trading-terminal language unless it is necessary to explain a safety boundary.
- Every metric should answer: "What does this mean?" and "Why should I care?"
- Every warning should be direct, not legalistic.
- The user should not need quant knowledge to understand whether evidence is strong or weak.
- Real-money language must be especially clear and conservative.
- Unsupported ideas should be described honestly instead of softened with vague confidence.
- Sample data should be called sample data, not evidence of a real market opportunity.

## Preferred Language

- Use "Historical Test" before "backtest."
- Use "Worst Drop" before "drawdown."
- Use "Gain/Loss Ratio" before "profit factor."
- Use "Market Mood" before "sentiment."
- Use "Reasons to Be Careful" before "quality issues."
- Use "Allowed to Use Real Money" before "live trading eligibility."
- Explain fixture-backed data as "sample data built into the app."
- Use "Simpler Idea It Must Beat" before "baseline."
- Use "Environment Fit" before "current regime fit."
- Use "Curve-Fit Risk" before "overfitting risk."
- Use "Research Ranking" before "ranking."
- Use "Overall Research Score" before "overall score."
- Use "Simpler Comparison" before "baseline comparison."
- Use "Cost Fragility" before "cost sensitivity."
- Use "Sample Size" before "trade count" when explaining ranking confidence.
- Use "Research Candidate" before "candidate."
- Use "Research Watchlist" before "watchlist."
- Use "What Supports It," "What Is Missing," and "What Would Change Our Mind" on candidate pages.
- Use "Built-In Sample Universe" before "fixture universe."
- Use "Pretend Portfolio Tests" before "model portfolio."
- Use "Cash Left Safely Unused" and explain cash as intentional.
- Use "Safety Rule" before "constraint."
- Use "Why It Appears" for every model holding.
- Use "Next Review Notes" before "monitoring."
- Use "Evidence Details" for technical portfolio numbers.
- Use "Next Review Item" before any future review trigger.
- Use "Same-Day Market Study" before "intraday."
- Use "First-Hour Window" before "first hour."
- Use "Opening Reference Level" before "opening benchmark."
- Use "Sit-Out Day" before "no-trade day."
- Use "Hypothetical Intraday Result" before intraday simulation output.
- Use "Research Spike Verdict" before spike verdict.
- Use "Paired Instrument Comparison" only when paired fixture data exists.
- Use "Historical Same-Day Sample Data" before "historical intraday data."
- Use "Local CSV Import" before "CSV ingestion."
- Use "Ready for Future Replay" before "session readiness."
- Use "Original Time Zone" before "source timezone."
- Use "Price Adjustment Note" before "adjustment mode."
- Use "Past Morning Practice Test" before "historical replay" or "replay engine."
- Use "Practice Setup" before "setup candidate."
- Use "Pretend Start" before "entry."
- Use "Pretend Finish" before "exit."
- Use "Pretend Result" before "hypothetical trade."
- Use "Keep Watching" before "no decision yet."
- Use "Not Enough Data" before "incomplete replay."
- Use "What Happened Afterward" before "post-signal result."
- Use "Why This Might Be Misleading" before "replay limitation."
- Use "What EdgeLab Should Test Next" before "next validation step."
- Use "Replay Clock" before "current replay timestamp."
- Use "Bars Visible So Far" before "visible bar count."
- Use "What EdgeLab Knew Then" before "point-in-time context."
- Use "Setup Marked for Research" before "detected setup."
- Use "No Future Peeking" before "look-ahead bias control."
- Use "Many-Morning Practice Test" before "multi-session replay."
- Use "Repeated Pattern Results" before "pattern statistics."
- Use "Sit-Out Review" before "no-trade analysis."
- Use "Not Enough Examples" before any sample-size warning.
- Use "Worth More Testing" only as a research next step, never as permission.
- Use "What Usually Happened" before outcome counts.
- Use "What EdgeLab Might Have Missed" before hindsight review.

## Portfolio Language Standard

- Put plain English before technical terms.
- Put the bottom line before numbers.
- The user should understand what EdgeLab thinks before seeing metrics.
- Technical terms belong in Evidence details, not the first screen.
- Real-money status must be unmistakable.
- Practice portfolios are not recommendations and should never sound actionable.

## Intraday Language Standard

- Put the bottom line before setup details.
- Explain synthetic sample data before any event or result.
- Use "Sit-Out Day" when no setup is supported.
- Keep setup mechanics in Evidence details when they get technical.
- Real-money status must be unmistakable.
- Intraday output is not live, not a signal system, and not a recommendation.
- Repeated intraday summaries should say "Not enough examples yet" when the local
  fixture set is tiny.
- Repeated pattern and sit-out review pages should put all technical counts in
  Evidence details.

## Safety Language

Real-money readiness should be stated plainly and conservatively. In the current phase, the answer
must be "No." The UI should not imply that a strategy is actionable because a number looks good.

Warnings should be short and direct:

- "This is not proof the strategy works."
- "This is not a recommendation."
- "The app is not reading live news yet."
- "Doing nothing is an acceptable outcome when evidence is thin."
- "This symbol belongs on a research screen, not a real-money decision list."
- "This pretend portfolio test is for research practice only."
- "Real-money status: Not allowed."
- "This synthetic intraday result is not live and not a signal system."
- "These are local historical files, not live market data."
- "First-hour completeness shows whether any regular first-hour minutes are missing."
- "Small gaps should be reviewed before trusting the replay."
- "This FirstRate study is local research only and not a recommendation."
- "Run local analysis" means start a deliberate local research review, not place an order.
- "Latest saved result" means the newest matching local research summary, not a current market view.
- "This saved result may be stale because the source file changed."
- "Copied-account scaling multiplies mistakes too."
- "SPY vs QQQ Pattern Study" means a local comparison, not a market instruction.
- "What Looked Different" should appear before technical comparison counts.
- "Too Noisy to Compare" means EdgeLab should slow down, not force an answer.
- "Early Move Failed" should appear before the technical name "Opening Range Failure."
- "Opening Range Failure" belongs in Evidence details as the technical setup name.
