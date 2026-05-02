# Wiki Index

## Concepts

- [Database](concepts/database.md) — A mock entity used in tests to represent a data storage component.

- [MOCK_EXTRACTION](concepts/mock_extraction.md) — A predefined dictionary representing a mock output from the LLM, used in tests t

- [Page promotion](concepts/page_promotion.md) — The process of elevating an entire wiki page to a higher conceptual tier based o

- [Fact promotion](concepts/fact_promotion.md) — The process of elevating a fact to a higher tier or marking it as 'consolidated'

- [procedural tier](concepts/procedural_tier.md) — The highest and most stable tier for facts and wiki pages, representing highly c

- [semantic tier](concepts/semantic_tier.md) — A more stable tier for facts and wiki pages, indicating a broader consensus or s

- [episodic tier](concepts/episodic_tier.md) — A intermediate tier for facts and wiki pages that have received some reinforceme

- [working tier](concepts/working_tier.md) — The initial and least stable tier for facts and wiki pages, representing newly a

- [PROCEDURAL_THRESHOLD](concepts/procedural_threshold.md) — The minimum confidence score required for a fact or page to be promoted to the '

- [SEMANTIC_TTL_DAYS](concepts/semantic_ttl_days.md) — A constant defining the Time-To-Live (in days) for facts or pages in the 'semant

- [EPISODIC_TTL_DAYS](concepts/episodic_ttl_days.md) — A constant defining the Time-To-Live (in days) for facts or pages in the 'episod

- [WORKING_TTL_DAYS](concepts/working_ttl_days.md) — A constant defining the Time-To-Live (in days) for facts or pages in the 'workin

- [CRUD Operations](concepts/crud_operations.md) — The fundamental set of Create, Read, Update, and Delete operations. This module 

- [Frontmatter](concepts/frontmatter.md) — The metadata block at the beginning of a markdown file, delimited by '---', cont

- [Exponential Backoff](concepts/exponential_backoff.md) — A retry strategy implemented in `LLMClient.generate` that increases the waiting 

- [Gemini API](concepts/gemini_api.md) — Google's generative AI platform, which provides models for tasks like text gener

- [_BATCH_CHAR_BUDGET](concepts/_batch_char_budget.md) — An integer representing the maximum character budget allowed for a single batch 

- [EXCLUDED_FILES](concepts/excluded_files.md) — A frozenset of specific file names that are always skipped during file scanning 

- [EXCLUDED_DIRS](concepts/excluded_dirs.md) — A frozenset of directory names that are always excluded from file scanning, rega

- [SUPPORTED_EXTENSIONS](concepts/supported_extensions.md) — A frozenset of file extensions that are considered processable source, configura

- [wiki update](concepts/wiki_update.md) — The process of modifying the project wiki based on information extracted from Gi

- [LLM extraction](concepts/llm_extraction.md) — The process of using a Large Language Model to identify and structure entities, 

- [dataclass](concepts/dataclass.md) — A Python decorator used for automatically generating methods like __init__, __re

- [json](concepts/json.md) — A standard Python library for working with JSON data, utilized by KnowledgeGraph

- [VALID_RELATION_TYPES](concepts/valid_relation_types.md) — A predefined set of valid strings representing the permissible types of relation

- [procedural](concepts/procedural.md) — The final consolidation tier for stable, high-confidence patterns, considered pe

- [semantic](concepts/semantic.md) — The third consolidation tier for distilled concepts across episodes, with high c

- [episodic](concepts/episodic.md) — The second consolidation tier for summaries of sessions/sprints, with moderate c

- [working](concepts/working.md) — The initial, high-volume, low-compression consolidation tier for facts from rece

- [Memory lifecycle](concepts/memory_lifecycle.md) — The overarching process by which facts and wiki pages transition through differe

- [Ebbinghaus retention decay](concepts/ebbinghaus_retention_decay.md) — A simplified model for the forgetting curve, applied to facts to decrease their 

- [Consolidation tiers](concepts/consolidation_tiers.md) — A system of information retention levels: working, episodic, semantic, and proce

- [Console Output](concepts/console_output.md) — The mechanism for displaying rich-formatted text, tables, and panels to the user

- [Configuration Management](concepts/configuration_management.md) — The handling of project-specific settings and parameters for llmwikidoc, includi

- [File Ingestion](concepts/file_ingestion.md) — The process of scanning and analyzing the current state of all specified project

- [Commit Ingestion](concepts/commit_ingestion.md) — The automated process of analyzing changes in a git commit, extracting relevant 

- [Wiki Initialization](concepts/wiki_initialization.md) — The setup process for the llmwikidoc wiki within a project, involving creating t

- [Git Post-Commit Hook](concepts/git_post-commit_hook.md) — A mechanism within Git that automatically executes a script (like `llmwikidoc in

- [CLI Entry Point](concepts/cli_entry_point.md) — The designated starting point for command-line execution of the llmwikidoc appli

- [app](concepts/app.md) — The central Typer application instance for the llmwikidoc CLI, configuring its n

- [__version__](concepts/__version__.md) — A string constant representing the current semantic version of the `llmwikidoc` 

- [UserService](concepts/userservice.md) — A mock entity frequently used in tests to represent a service responsible for us

- [pyinstaller](concepts/pyinstaller.md) — A development dependency used to bundle Python applications into standalone exec

- [hatchling](concepts/hatchling.md) — The build backend used for packaging the llmwikidoc project.

- [winget](concepts/winget.md) — The Windows Package Manager used to install Python on Windows systems.

- [uv](concepts/uv.md) — A Python package installer and manager, recommended for installing llmwikidoc gl

- [git hook](concepts/git_hook.md) — A script installed by the `llmwikidoc init` command that triggers wiki updates u

- [Python](concepts/python.md) — The programming language runtime required for executing the llmwikidoc applicati

- [.llmwikidoc.toml](concepts/llmwikidoctoml.md) — The TOML-formatted configuration file used to persist project settings for llmwi

- [wiki/](concepts/wiki.md) — The directory created by `llmwikidoc init` where the generated and updated wiki 

- [gemini-embedding-001](concepts/gemini-embedding-001.md) — The embedding model used for generating vector representations of text for searc

- [pytest-mock](concepts/pytest-mock.md) — A pytest plugin for mocking objects in tests.

- [pytest](concepts/pytest.md) — The testing framework used for llmwikidoc, with tests located in the 'tests' dir

- [tomllib](concepts/tomllib.md) — A standard library module (Python 3.11+) for parsing TOML files.

- [tomli](concepts/tomli.md) — A Python library for parsing TOML files.

- [rank-bm25](concepts/rank-bm25.md) — A Python library implementing the BM25 ranking function for text search.

- [networkx](concepts/networkx.md) — A Python library used by KnowledgeGraph for the creation, manipulation, and stud

- [gitpython](concepts/gitpython.md) — A Python library providing an object-oriented interface to Git repositories.

- [google-genai](concepts/google-genai.md) — A Python client library for interacting with Google's Gemini LLM models.

- [rich](concepts/rich.md) — A Python library for rich text and beautiful formatting in the terminal.

- [typer](concepts/typer.md) — A Python library used for building command-line interface applications.

- [Environment Variable API Key](concepts/environment_variable_api_key.md) — A design decision to manage the GEMINI_API_KEY via environment variables, rather

- [In-repo Wiki](concepts/in-repo_wiki.md) — A design decision to store the 'wiki/' directory directly within the documented 

- [Cached Embeddings](concepts/cached_embeddings.md) — A design decision to cache generated vector embeddings, recalculating them only 

- [JSON LLM Output](concepts/json_llm_output.md) — A design decision to use 'response_mime_type="application/json"' with Gemini for

- [Post-commit Non-blocking](concepts/post-commit_non-blocking.md) — A design decision ensuring that the 'post-commit' Git hook will not block the co

- [Markdown Frontmatter](concepts/markdown_frontmatter.md) — YAML metadata embedded at the top of markdown wiki pages to store structured inf

- [Session Crystallization](concepts/session_crystallization.md) — The process of generating structured summaries from N commits, creating new know

- [Retention Decay](concepts/retention_decay.md) — A mechanism based on Ebbinghaus's forgetting curve, where fact confidence scores

- [Consolidation Tiers](concepts/consolidation_tiers.md) — A memory management strategy involving progressive compression of wiki content t

- [Reciprocal Rank Fusion](concepts/reciprocal_rank_fusion.md) — An algorithm used to combine multiple ranked lists into a single, more robust ra

- [Confidence Scoring](concepts/confidence_scoring.md) — A system to assign and update reliability scores to facts extracted and stored i

- [Hybrid Search](concepts/hybrid_search.md) — A search methodology combining BM25, vector embeddings, and graph traversal for 

- [Knowledge Graph](concepts/knowledge_graph.md) — A structured representation of entities and their relationships within the proje

- [LLM Wiki Pattern](concepts/llm_wiki_pattern.md) — The conceptual framework for structuring the wiki, extended to version 2.

- [post-commit](concepts/post-commit.md) — A Git hook template that automatically triggers the llmwikidoc ingestion process

- [Workflow Rules](concepts/workflow_rules.md) — A set of guidelines in CLAUDE.md for developers, emphasizing planning, clarity, 

- [Project Status](concepts/project_status.md) — A section in CLAUDE.md that describes the current development stage of the proje

- [CodeGraph](concepts/codegraph.md) — A semantic code knowledge graph tool that is initialized and will index source f

- [search weights](concepts/search_weights.md) — A set of configuration parameters defining the weighting for different search co

- [confidence settings](concepts/confidence_settings.md) — A set of configuration parameters defining the initial, reinforcement, contradic

- [context_depth](concepts/context_depth.md) — A configuration parameter defining the depth of context for the LLM.

- [wiki_dir](concepts/wiki_dir.md) — A configuration parameter specifying the output directory for the generated wiki

- [gemini-2.5-flash](concepts/gemini-25-flash.md) — The default large language model chosen for its balance of cost and quality for 

- [git commit hook](concepts/git_commit_hook.md) — A git hook installed by `llmwikidoc init` that automatically runs `llmwikidoc in

- [digest](concepts/digest.md) — A summarized collection of information or changes within the wiki.

- [tier promotion](concepts/tier_promotion.md) — The process of elevating facts or pages through different knowledge tiers (e.g.,

- [README.md](concepts/readmemd.md) — The main documentation file for the project, providing setup and usage instructi

- [.gitignore](concepts/gitignore.md) — Configuration file specifying intentionally untracked files that Git should igno

- [procedural facts](concepts/procedural_facts.md) — Facts that are highly stable, have numerous sources (e.g., 5+), and very high co

- [memory tiers](concepts/memory_tiers.md) — Categorizations for facts (working, episodic, semantic, procedural) based on the

- [Ebbinghaus decay](concepts/ebbinghaus_decay.md) — A memory decay model applied to fact confidence, where confidence decreases over

- [git commit](concepts/git_commit.md) — A record of changes to the codebase, serving as the primary input for the ingest

- [llmwikidoc status](concepts/llmwikidoc_status.md) — A command to check the current status of the `llmwikidoc` system or wiki.

- [llmwikidoc query](concepts/llmwikidoc_query.md) — A command to query the project wiki for information using natural language.

- [llmwikidoc ingest](concepts/llmwikidoc_ingest.md) — A command (often run via a git hook) to process new code changes and update the 

- [llmwikidoc init](concepts/llmwikidoc_init.md) — A command to initialize `llmwikidoc` in a git project, installing necessary hook

- [hook](concepts/hook.md) — A Git hook installed by `llmwikidoc init` to automate wiki updates on commit.

- [wiki](concepts/wiki.md) — The project knowledge base managed by the `llmwikidoc` tool.

- [GEMINI_API_KEY](concepts/gemini_api_key.md) — An environment variable that must be set with a valid key for the Google GenAI s

- [llmwikidoc](concepts/llmwikidoc.md) — The overall project and tool, a Python CLI for wiki generation.

## Modules

- [pytest](entities/pytest.md) — A popular testing framework for Python, used here to define and run unit tests f

- [llmwikidoc.wiki](entities/llmwikidocwiki.md) — The core module responsible for managing wiki files, offering functionalities fo

- [llmwikidoc.search](entities/llmwikidocsearch.md) — The module responsible for orchestrating a multi-stream hybrid search functional

- [google.genai](entities/googlegenai.md) — The official Python client library for interacting with Google's Generative AI A

- [llmwikidoc.llm](entities/llmwikidocllm.md) — The main module providing the `LLMClient` for interacting with the Google Gemini

- [ingest.py](entities/ingestpy.md) — The main module for the ingestion pipeline, orchestrating the process from readi

- [llmwikidoc.graph](entities/llmwikidocgraph.md) — Module responsible for defining the KnowledgeGraph data structure and its associ

- [llmwikidoc.cli](entities/llmwikidoccli.md) — The main module for the llmwikidoc command-line interface, orchestrating various

- [pytest-mock](entities/pytest-mock.md) — A development dependency that provides mocking utilities for pytest tests.

- [typer](entities/typer.md) — A Python library for building command-line applications, used for llmwikidoc's C

- [tomli-w](entities/tomli-w.md) — A Python library for writing TOML files.

- [tomli](entities/tomli.md) — A Python library for parsing TOML files.

- [rich](entities/rich.md) — A Python library for adding rich text and beautiful formatting to terminal outpu

- [rank-bm25](entities/rank-bm25.md) — A Python library providing an implementation of the BM25 ranking function, likel

- [networkx](entities/networkx.md) — A Python library for the creation, manipulation, and study of the structure, dyn

- [google-genai](entities/google-genai.md) — A Python library for integrating with Google's Generative AI models.

- [gitpython](entities/gitpython.md) — A Python library providing an API for interacting with Git repositories.

- [llmwikidoc](entities/llmwikidoc.md) — The primary package for an LLM-powered wiki designed to be auto-updated from git

- [lint](entities/lint.md) — Performs health checks, detects contradictions, and identifies issues in the wik

- [search](entities/search.md) — Implements the hybrid search functionality for querying the wiki.

- [confidence](entities/confidence.md) — Module responsible for managing the confidence scores of facts, including their 

- [graph](entities/graph.md) — Manages the project's knowledge graph, including adding nodes and edges.

- [wiki](entities/wiki.md) — Manages the creation, updating, and organization of markdown wiki files and stru

- [llm](entities/llm.md) — Provides an interface for interacting with the Gemini LLM for content extraction

- [ingest](entities/ingest.md) — A Typer command to process and ingest a specific git commit (or HEAD by default)

- [git_reader](entities/git_reader.md) — Extracts detailed context and data from Git commits.

- [config](entities/config.md) — Module responsible for loading, defining, and managing the project's configurati

- [cli](entities/cli.md) — The main command-line interface module, handling user interactions and commands.

- [main.py](entities/mainpy.md) — The main Python script for the project, containing a simple entry point function

- [CLAUDE.md](entities/claudemd.md) — A Markdown file providing guidance, project status, name, workflow rules, and to

- [.llmwikidoc.toml](entities/llmwikidoctoml.md) — The configuration file for the llmwikidoc project, defining model, wiki director

- [consolidate.py](entities/consolidatepy.md) — A module responsible for managing confidence decay, promoting facts and pages be

- [llmwikidoc.consolidate](entities/llmwikidocconsolidate.md) — The module responsible for implementing the memory lifecycle, including Ebbingha

- [tests/test_consolidate.py](entities/teststest_consolidatepy.md) — The test suite for the `llmwikidoc.consolidate` module, covering Ebbinghaus deca

## Classs

- [BM25Okapi](entities/bm25okapi.md) — An external class from the `rank_bm25` library, implementing the BM25 ranking fu

- [WikiPage](entities/wikipage.md) — Represents a single page within the wiki, holding its content, frontmatter metad

- [HybridSearch](entities/hybridsearch.md) — The primary search class that orchestrates three distinct search streams (BM25, 

- [EmbeddingCache](entities/embeddingcache.md) — A utility class that manages the persistence and retrieval of vector embeddings,

- [SearchResult](entities/searchresult.md) — A dataclass representing a single result from the hybrid search, containing the 

- [IngestAllFilesResult](entities/ingestallfilesresult.md) — A dataclass that encapsulates the results of a file ingestion operation, includi

- [CommitContext](entities/commitcontext.md) — A data structure encapsulating all relevant information about a Git commit, such

- [LLMClient](entities/llmclient.md) — Represents a client interface for interacting with a Large Language Model, used 

- [SkippedCommit](entities/skippedcommit.md) — An exception raised when a Git commit is deemed irrelevant or has no changes to 

- [IngestResult](entities/ingestresult.md) — A dataclass that encapsulates the results of processing a single Git commit, inc

- [pathlib.Path](entities/pathlibpath.md) — A Python standard library class used for representing file system paths, enablin

- [KnowledgeGraph](entities/knowledgegraph.md) — A class representing a graph database for storing and managing project entities 

- [DigestResult](entities/digestresult.md) — A data class that encapsulates the structured output of the `create_digest` func

- [Config](entities/config.md) — A configuration class for the LLMWikiDoc project, managing various project-wide 

- [SearchConfig](entities/searchconfig.md) — A dataclass holding parameters that define the weighting for different search co

- [ConfidenceConfig](entities/confidenceconfig.md) — A configuration class specifically for confidence-related settings within the LL

- [WikiManager](entities/wikimanager.md) — A class responsible for managing the wiki's pages, including creation, updates, 

- [ConsolidationResult](entities/consolidationresult.md) — A data class that aggregates the results of a consolidation run, tracking metric

- [Fact](entities/fact.md) — Represents a single verifiable fact within the wiki, including its statement, as

- [ConfidenceStore](entities/confidencestore.md) — A class managing the storage, retrieval, and manipulation of Fact objects, inclu

## Functions

- [default_config](entities/default_config.md) — A pytest fixture providing a default Config instance initialized for testing, us

- [tmp_project](entities/tmp_project.md) — A pytest fixture providing a temporary directory structured to simulate a Git pr

- [make_store](entities/make_store.md) — A test utility function that creates a new instance of ConfidenceStore with a te

- [_safe_filename](entities/_safe_filename.md) — Converts an input string (typically a page name) into a safe, lowercase, and fil

- [render_frontmatter](entities/render_frontmatter.md) — Serializes a given frontmatter dictionary and body string back into a complete m

- [parse_frontmatter](entities/parse_frontmatter.md) — Extracts and parses the YAML-like frontmatter from a markdown string, returning 

- [_content_hash](entities/_content_hash.md) — A utility function that generates a SHA256 hash (truncated to 16 characters) of 

- [_cosine_similarity](entities/_cosine_similarity.md) — A utility function that calculates the cosine similarity between two given lists

- [_tokenize](entities/_tokenize.md) — A simple utility function that tokenizes a given text string by extracting lower

- [_page_text](entities/_page_text.md) — A helper function that extracts and combines the name and body content of a Wiki

- [_reciprocal_rank_fusion](entities/_reciprocal_rank_fusion.md) — A utility function that combines multiple ranked lists of search results (repres

- [LLMClient.__exit__](entities/llmclient__exit__.md) — Ensures that the `LLMClient`'s internal client connection is closed when exiting

- [LLMClient.__enter__](entities/llmclient__enter__.md) — Allows the `LLMClient` to be used as a context manager, returning the instance i

- [LLMClient.close](entities/llmclientclose.md) — Closes the internal Google Gemini API client connection.

- [LLMClient.embed](entities/llmclientembed.md) — Generates an embedding vector for a given input text using the 'gemini-embedding

- [LLMClient.generate_structured](entities/llmclientgenerate_structured.md) — Generates a JSON response from Gemini by calling `generate` with `json_output=Tr

- [LLMClient.generate](entities/llmclientgenerate.md) — Sends a text prompt to the Gemini model and returns the text response, optionall

- [LLMClient.__init__](entities/llmclient__init__.md) — Initializes the `LLMClient` with a configuration object and sets up the underlyi

- [_apply_extraction](entities/_apply_extraction.md) — Takes the structured data extracted by the LLM and applies it to the wiki, knowl

- [_format_files](entities/_format_files.md) — Formats a dictionary of file paths and their contents into a markdown string sui

- [_build_file_extraction_prompt](entities/_build_file_extraction_prompt.md) — Constructs the detailed prompt for the LLM, including the list of files being an

- [_extract_from_files](entities/_extract_from_files.md) — Interacts with the LLM client to generate structured information (summary, entit

- [_batch_files](entities/_batch_files.md) — Groups a list of file paths into batches by their parent directory, ensuring tha

- [scan_files](entities/scan_files.md) — Scans a given project root directory to find all processable files, excluding sp

- [ingest_all_files](entities/ingest_all_files.md) — The primary function that orchestrates the file scanning, batching, LLM extracti

- [_build_summary_body](entities/_build_summary_body.md) — Generates the markdown content for a commit summary page in the wiki, incorporat

- [_format_file_contents](entities/_format_file_contents.md) — A helper function responsible for formatting and potentially truncating file con

- [_build_extraction_prompt](entities/_build_extraction_prompt.md) — A helper function that constructs the detailed prompt for the LLM, including com

- [_extract](entities/_extract.md) — Builds an LLM prompt from the commit context and calls the LLM for structured in

- [ingest_commit](entities/ingest_commit.md) — A function that processes a Git commit by using an LLM to extract structured inf

- [KnowledgeGraph._load](entities/knowledgegraph_load.md) — Internal method to load the graph's state from its designated file path, parsing

- [KnowledgeGraph.save](entities/knowledgegraphsave.md) — Persists the current state of the graph to its designated file path, serializing

- [KnowledgeGraph.edge_count](entities/knowledgegraphedge_count.md) — A property that returns the total number of relationship edges currently stored 

- [KnowledgeGraph.node_count](entities/knowledgegraphnode_count.md) — A property that returns the total number of entity nodes currently stored in the

- [KnowledgeGraph.search_entities](entities/knowledgegraphsearch_entities.md) — Searches for and returns entity names that contain a specified query string, per

- [KnowledgeGraph.entity_info](entities/knowledgegraphentity_info.md) — Retrieves comprehensive information for a given entity, including its attributes

- [KnowledgeGraph.find_path](entities/knowledgegraphfind_path.md) — Finds the shortest path between two specified entities within the graph using Ne

- [KnowledgeGraph.dependents](entities/knowledgegraphdependents.md) — Returns a list of entities that have incoming edges to the specified entity, ind

- [KnowledgeGraph.neighbors](entities/knowledgegraphneighbors.md) — Returns a list of entities directly connected from a given entity, with an optio

- [KnowledgeGraph.add_relation](entities/knowledgegraphadd_relation.md) — Adds a typed, directed edge between two entities, ensuring both entities exist i

- [KnowledgeGraph.add_entity](entities/knowledgegraphadd_entity.md) — Adds a new entity node to the graph or updates the type and description attribut

- [KnowledgeGraph.__init__](entities/knowledgegraph__init__.md) — Initializes a KnowledgeGraph instance, setting up its file path and loading exis

- [create_digest](entities/create_digest.md) — Generates a structured summary or 'digest' of recent changes, facts, and open qu

- [_compress_page](entities/_compress_page.md) — Utilizes an LLM to compress the body of a WikiPage when it is promoted to a high

- [_promote_pages](entities/_promote_pages.md) — Analyzes wiki pages and their associated facts to determine if the page's tier s

- [run_consolidation](entities/run_consolidation.md) — Orchestrates the entire consolidation process, invoking decay, fact promotion, a

- [_find_project_root](entities/_find_project_root.md) — Identifies the root directory of a project by searching for a '.git' folder in t

- [write_default](entities/write_default.md) — Writes a default project configuration file, '.llmwikidoc.toml', to a specified 

- [load](entities/load.md) — Loads the project configuration from a '.llmwikidoc.toml' file located within th

- [_now_iso](entities/_now_iso.md) — Generates the current UTC datetime formatted as an ISO 8601 string (e.g., 'YYYY-

- [_fact_key](entities/_fact_key.md) — A utility function to generate a unique string key for a fact based on its entit

- [ingestall](entities/ingestall.md) — A Typer command that scans all supported project files (excluding the wiki direc

- [_print_ingest_result](entities/_print_ingest_result.md) — A helper function that displays a formatted summary of the results after a singl

- [_ingest_all](entities/_ingest_all.md) — A helper function used by the 'ingest --all' command to iterate through all past

- [_hook_script](entities/_hook_script.md) — Generates the shell script content for the 'post-commit' git hook, which trigger

- [_install_hook](entities/_install_hook.md) — A helper function responsible for installing or updating the 'post-commit' git h

- [init](entities/init.md) — A Typer command to initialize the llmwikidoc project within a git repository by 

- [llmwikidoc status](entities/llmwikidoc_status.md) — CLI command to display various statistics about the current state of the wiki.

- [llmwikidoc lint](entities/llmwikidoc_lint.md) — CLI command to run health checks and detect inconsistencies in the wiki content.

- [llmwikidoc query](entities/llmwikidoc_query.md) — CLI command to query the wiki using natural language, leveraging hybrid search a

- [llmwikidoc ingest](entities/llmwikidoc_ingest.md) — CLI command to manually trigger the ingestion pipeline for the latest commit.

- [llmwikidoc init](entities/llmwikidoc_init.md) — CLI command to initialize the wiki directory, install the Git hook, and create t

- [main](entities/main.md) — The primary function in main.py, which prints a greeting message.

- [_tier_stability_multiplier](entities/_tier_stability_multiplier.md) — Returns a multiplier that indicates how resistant a fact's confidence decay shou

- [_compute_new_tier](entities/_compute_new_tier.md) — Calculates the target tier for a fact or page given its current tier, confidence

- [_fact_tier](entities/_fact_tier.md) — Determines the current tier ('working', 'episodic', 'semantic', 'procedural') of

- [_promote_facts](entities/_promote_facts.md) — Evaluates facts for promotion based on criteria like age, confidence, and number

- [_apply_decay](entities/_apply_decay.md) — Applies the Ebbinghaus decay algorithm to facts within the ConfidenceStore, redu
