# Cursor Commands

This folder contains custom Cursor IDE commands that provide specialized workflows for development tasks in the UnifAI project.

## What are Cursor Commands?

Cursor commands are AI-powered workflows that you can invoke by referencing them with the `/` symbol in the Cursor chat. Each command file contains specific instructions that guide the AI through complex, multi-step processes.

## Available Commands

### 📋 review.md - Code Review

Performs automated code reviews on your current branch with varying depth levels.

**Usage:**
```
/UnifAI/review [basic|deep] [files/folders]
```

**Parameters:**
- `basic` (default): Quick review focusing on obvious issues
- `deep`: Comprehensive review including design validation
- `files/folders` (optional): Specify particular files or folders to review

**Output:**
Creates a review file named `<branch_name>_<review_type>_review.md` containing:
1. Short overview of the feature and its purpose
2. Issues found, organized by area and severity
3. Design reference (for deep reviews or when architecture.md exists)

**Example:**
```
/UnifAI/review deep src/components/
```

---

### 🎨 /design - Design Document Generator

Creates architecture design documents based on Jira ticket requirements.

**Prerequisites:**
- Jira integration configured (via MCP or other method)
- Access to `.cursor/files/ADR - Architecture Review Template.md`

**Usage:**
```
/UnifAI/design <jira-ticket-id>
```

**Process:**
1. Validates Jira connectivity
2. Fetches ticket information
3. Generates design document in both Markdown and HTML formats
4. Follows ADR (Architecture Decision Record) template structure

**Output:**
Two files with identical content:
- `<ticket-id>_design.md`
- `<ticket-id>_design.html`

**Example:**
```
/UnifAI/design GENIE-1163
```

---

### 📤 /push - Design Document Uploader

Uploads design files to specified Jira tickets.

**Prerequisites:**
- Jira integration configured
- Design file already created

**Usage:**
```
/UnifAI/push <jira-ticket> <file-name>
```

**Parameters:**
- `jira-ticket`: The Jira ticket ID to upload to
- `file-name`: Path to the design file to upload

**Example:**
```
/UnifAI/push GENIE-1163 GENIE-1163_design.html
```

---

## Setup Requirements

### Jira Integration

The `design` and `push` commands require Jira connectivity. Ensure you have one of the following configured:

1. **MCP Server** - Jira MCP server in your Cursor settings
2. **API Credentials** - Jira API tokens configured in your environment

If Jira integration is not available, the commands will notify you and stop execution.

### Template Files

The `design` command requires:
- `.cursor/files/ADR - Architecture Review Template.md`

Ensure this file exists in your project structure.

---

## Best Practices

### For Code Reviews

1. **Run basic reviews frequently** during development
2. **Run deep reviews** before:
   - Creating pull requests
   - Merging to main branches
   - Releasing features
3. **Target specific areas** when reviewing large changes
4. **Address all severity levels** in the review output

### For Design Documents

1. **Create designs early** in the feature development lifecycle
2. **Update designs** when significant changes occur
3. **Reference architecture.md files** in relevant folders
4. **Push designs to Jira** for team visibility and collaboration

---

## Creating New Commands

To add a new command:

1. Create a new `.md` file in this folder
2. Write clear instructions for the AI to follow
3. Include parameter specifications and expected outputs
4. Update this README with documentation
5. Test the command thoroughly before committing

---

## Troubleshooting

**Command not found:**
- Ensure you're using `@` followed by the command filename (e.g., `@review.md`)
- Check that the file exists in `.cursor/commands/`

**Jira connection errors:**
- Verify Jira MCP server is running
- Check API credentials and permissions
- Confirm network connectivity to Jira instance

**Review file not generated:**
- Ensure you're on a git branch (not detached HEAD)
- Check write permissions in the current directory
- Verify there are changes to review on the branch

---

## Contributing

When modifying commands:
1. Test changes thoroughly
2. Update this README if behavior changes
3. Consider backward compatibility
4. Document any new parameters or options

---

**Last Updated:** February 2026  
**Project:** UnifAI  
**Maintained by:** Development Team
