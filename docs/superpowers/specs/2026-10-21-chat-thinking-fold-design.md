# Chat thinking fold — Design

**Date:** 2026-10-21  
**Status:** approved

## Goal

Pipeline progress as conversational phrases **inside the bot bubble**, with PipelineFlow on top. Collapsible «Размышления»; auto-collapse when the answer (chat_summary) arrives. No ThinkingBar above composer.

## Behavior

1. Pending bubble: Flow → open thinking fold → live phrases.
2. Phrases: varied templates by stage + detail + timed micro-beats (not LLM).
3. Done: fold collapses by default (expandable); summary + ArtifactCard below.
4. More than coarse stages: per-chart/per-figure lines + extra beats while a stage lasts.
