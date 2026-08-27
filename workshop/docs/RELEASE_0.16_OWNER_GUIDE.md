# Release 0.16 Owner Guide

## Build

Open Sanctuary → Crossroads → Build, then choose **Open Build Work Order Builder**. Add up to four registered sources and/or enter owner build notes, choose a fixed work-order type, and complete only the fields that matter. Review and approve the plan before generation. Review and approve the result separately before saving or exporting.

The saved `build-work-order-draft` remains inactive. It can be reopened from My Work, exported locally as TXT, Markdown, or JSON, and rolled back while unchanged. The builder does not run code, invoke a shell, change project files, submit to Codex, or deploy.

## Modules

Open Sanctuary → Crossroads → Modules. The registry cards show static local registration truth. **AVAILABLE** means enabled by the Workshop configuration; **INACTIVE** means the entry is disabled. Neither label proves a process is running.

Choose **Open Module Proposal Builder** to describe a future local tool, worker, adapter, importer, exporter, media tool, research tool, system utility, or experimental module. The same separate plan/result approvals and inactive save apply. A proposal never installs, downloads, executes, activates, or fetches dependencies.

## Settings

Settings retains the existing Workshop-local owner name, companion name, speech preference, and reduced-motion preference. Save applies them locally and refresh preserves them. No Windows or browser-global setting is changed.

## Safety and recovery

Registered sources remain unchanged and stale hashes block approval. Refresh or restart recovers the recorded job state without silently resuming a state-changing action. Rollback removes only the unchanged draft created by that job; audit receipts remain.
