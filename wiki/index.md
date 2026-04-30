# Wiki Index

## Concepts

- [git commit hook](concepts/git_commit_hook.md) — A git hook installed by `llmwikidoc init` that automatically runs `llmwikidoc in

- [digest](concepts/digest.md) — A summarized collection of information or changes within the wiki.

- [tier promotion](concepts/tier_promotion.md) — The process of elevating facts or pages through different knowledge tiers (e.g.,

- [README.md](concepts/readmemd.md) — The main documentation file for the project, providing setup and usage instructi

- [.gitignore](concepts/gitignore.md) — Configuration file specifying intentionally untracked files that Git should igno

- [procedural facts](concepts/procedural_facts.md) — Facts that are highly stable, have numerous sources (e.g., 5+), and very high co

- [memory tiers](concepts/memory_tiers.md) — Categorizations for facts (working, episodic, semantic, procedural) based on the

- [Ebbinghaus decay](concepts/ebbinghaus_decay.md) — A mechanism to model the natural decay of confidence in facts over time, similar

- [git commit](concepts/git_commit.md) — A standard Git command that, when used with `llmwikidoc`, triggers the wiki upda

- [llmwikidoc status](concepts/llmwikidoc_status.md) — A command to check the current status of the `llmwikidoc` system or wiki.

- [llmwikidoc query](concepts/llmwikidoc_query.md) — A command to query the project wiki for information using natural language.

- [llmwikidoc ingest](concepts/llmwikidoc_ingest.md) — A command (often run via a git hook) to process new code changes and update the 

- [llmwikidoc init](concepts/llmwikidoc_init.md) — A command to initialize `llmwikidoc` in a git project, installing necessary hook

- [hook](concepts/hook.md) — A Git hook installed by `llmwikidoc init` to automate wiki updates on commit.

- [wiki](concepts/wiki.md) — The project knowledge base managed by the `llmwikidoc` tool.

- [GEMINI_API_KEY](concepts/gemini_api_key.md) — An environment variable required for `llmwikidoc` to interact with the Gemini AP

- [llmwikidoc](concepts/llmwikidoc.md) — A tool designed to manage a project wiki by integrating with Git commits to upda

## Modules

- [consolidate.py](entities/consolidatepy.md) — A module responsible for managing confidence decay, promoting facts and pages be

- [llmwikidoc.consolidate](entities/llmwikidocconsolidate.md) — A module responsible for consolidating wiki knowledge, including managing confid

- [tests/test_consolidate.py](entities/teststest_consolidatepy.md) — A new test module for the `consolidate.py` script, covering Ebbinghaus decay, ti

## Classs

- [WikiManager](entities/wikimanager.md) — Manages the wiki structure and content.

- [ConsolidationResult](entities/consolidationresult.md) — Stores the outcomes and metrics of a consolidation operation, such as facts deca

- [Fact](entities/fact.md) — Represents a single verifiable statement within the wiki, including its confiden

- [ConfidenceStore](entities/confidencestore.md) — Manages the storage and retrieval of facts and their associated confidence level

## Functions

- [_tier_stability_multiplier](entities/_tier_stability_multiplier.md) — Provides a multiplier that affects the decay rate of facts based on their curren

- [_compute_new_tier](entities/_compute_new_tier.md) — Calculates the potential new knowledge tier for a fact or page based on its curr

- [_fact_tier](entities/_fact_tier.md) — Determines the current knowledge tier of a fact based on its number of sources a

- [_promote_facts](entities/_promote_facts.md) — Promotes facts within the ConfidenceStore by adding a 'consolidated' source mark

- [_apply_decay](entities/_apply_decay.md) — Applies the Ebbinghaus decay logic to facts in the ConfidenceStore, reducing the
