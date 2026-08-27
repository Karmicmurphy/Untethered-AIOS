# Local API Worker Kit 0.8 Owner Guide

## What it is

The Workshop now has four small local workers. Each handles one supported job,
shows its plan before running, and shows its result before you accept it.

They work locally. They do not use a model, internet worker, shell, automatic
plugin, or arbitrary file path.

## Start from Talk

Open a saved Talk session. In **Supported local workers**, choose:

- **Inspect this approved Talk** to read the current transcript and report exact
  size, encoding, lines, and content;
- **Show code structure** to inspect pasted code without running it;
- **Make a note from selected text** after selecting a passage in the visible
  transcript.

If no passage is selected for the note action, the plan clearly uses the
complete current Talk source.

## Start from Write

Open a saved Write document. In **Supported local workers**, choose:

- **Inspect this approved writing**;
- **Show code structure**;
- **Make a note from selected text**.

Your current saved Write document remains the source. A note is only a
proposal until both the plan and result are separately approved.

## Start from My Work

Open **My Work** and find **Supported local workers**.

1. Choose a supported action.
2. Choose visible work from the current project.
3. Optionally describe the exact purpose.
4. For package validation, optionally list expected safe relative member paths
   and known SHA-256 hashes.
5. Select **Prepare worker plan**.

You do not need an artifact ID, job ID, database query, or file path.

## Review the plan

The plan tells you:

- which worker was chosen;
- which visible source it will read;
- what it will do;
- what it may create;
- what it cannot access;
- that completion remains unattached and inactive.

Add a short approval note and choose **Approve plan**. This still does not run
the worker. Choose **Run approved worker** separately.

Rejecting or cancelling runs nothing.

## Review the result

A completed result is validated but not yet accepted. You can inspect:

- exact text facts and readable content;
- code facts separately from heuristic findings;
- a complete proposed note;
- package members, hashes, missing, unexpected, unsafe, duplicate, and mismatch
  findings;
- evidence count and unattached/inactive state.

Add a short note to approve. Rejection accepts nothing.

For Approved Text Reader, Code Structure Inspector, and Package Manifest
Validator, approval records your decision but changes no source.

For Note Proposal Worker, approval creates one new draft note. It never changes
the Talk, Write, or artifact it came from.

## Rollback and history

An accepted worker note has **Roll back created note**. Rollback removes only
that unchanged job-created note and preserves the source and unrelated work.
If the note changed, automatic rollback stops safely.

Worker job history is in My Work. A terminal job can be cleaned after any
created note is rolled back. Cleanup removes the job view and technical
evidence rows but preserves receipts.

If the companion restarts during a running job, the job becomes safely
interrupted. No output is accepted, attached, or activated. Use **Recover
interrupted job** to return to the still-current approved plan, or cancel it.

## Honest limits

Release 0.8 supports only these four workers. It refuses arbitrary shell,
Python, commands, paths, internet work, folder scanning, installation, import,
attachment, activation, and module promotion.

Code inspection is lexical, not a claim of semantic understanding. Package
validation proves only the members and hashes it could inspect. Validated
output is evidence, not proof, and never substitutes for your decision.
