# About

This project tracking tool is a very personal and opinionated way to keep track of my own ideas for personal projects, software or digital products and such other initiatives. It's a mix of a To-Do list combined with tracking and project managment, but not traditional project management tools with Gantt diagrams and such other useless things, or agile's user stories etc, more just notes and tasks around the logical grouping idea of a project in perhaps the vaguest sense and geared towards work with AI tools.

# Main concepts

The top first class citizen here is just the idea of **Project**. What it means in the context of this particular tool is more like a stateful bag of properties that transition through a kanban-style lightweight lifecycle.

A project will have

- project names (work in progress name, tentative final name)

- description & vision

- creation date

- stated goal, why am I doing this project

- criteria for completion or abandonment

- desired end date, to avoid stalling for ever 

- link to a github repo

- optionally a website

- star rating (1 to 5) for myself

- a completion percentage based on tasks done

- another completion percentage which is my subjective apprisal

- associated local dir in my dev or work machine

- any number of **Notes** (these are just text - plain or markdown - and links, or could be notes I take about blockers, doubts etc)

- A number of **Tasks** that can just be "new", "in progress" or "done". at the same time tasks can have Notes associated to it too.

- Any number of associated pdf or word reference files used in research, or as input etc as well as any number of .md files, for example if I am working with certain contexts with Claude or other similar tools. This could be things like

	- voice.md, for registering a specific authoring voice if the project is about content writing

	- .md files can be structured inside a folder with skills, personalities etc

- A project can have colaborators

 

Project entities can be grouped into **Areas**. Default areas can be **Software products**, **Writings**, **Personal Products**, **Digital Products**, but I can create or delete an **Area**. Deleting an Area does not delete the projects, it just ungroups them.

# UI

There will be a dir tree on the left side of the screen on a collapsible panel, where I will see all projects. 

	- I can search by name

	- I can filter by groups or name

	- I can sort alphabetically

	- Or by date asc or desc

I can archive a project into a specific "Archive" folder. Projects and associated files are never deleted.

In any given project I can reference artifacts and notes and everything else from any other projects.

I can only work on a project at once, but I can browse the tree and drag and drop a file reference from another project

When I want to add tasks to an existing project a popup will open where I can describe the task. If I paste a bullet or ordered list the system will understand those are each a task and will create a task for each item in the list

On the main portion on the screen I can have two things, or two modes.

- write mode, similar to Cursor's Zen Mode. Screen is divided in two, markdown and preview.

- chat mode, where I can engage with LLM's to work on a project. Refer to section *Model Usage* below in this document. Let's say I am using Claude behind the scenes here (this tool would therefore be a wrapper), therefore I will have a ChatGPT style screen with Chat and conversation

- English and Spanish toggle

- dark & light modes

- minimalistic zen style

- ability to change fonts

- different notes and artifacts in different projects can have different fonts and colors for highlight and visual cueing think some WYSIWYG possibilities. I know that contradicts markdown everywhere as a standard but let's see what we can do

- Use emojis sparingly (only things like check marks, warning, stops, rockets and little else, gitmoji standard at most)

# Additional functionality

## Commands

These are to be performed via the UI

- from a given **Project** entity I should be able to derive the following:

	- PRD.json in a style suitable for a Ralph loop or a standard coding assistant

	- Similar BRD and MRD documents (for business and marketing, respectively)

- generate content for a social network like LinkedIN or Twitter

- I can open a Claude CLI on the project's dir

- I can open a project's dir or repo in Cursor or Code or any other IDE, therefore I should have at least the option to edit a yaml file on screen to edit this. No need ot build a fancy UI around that functionality.

- I can export everything that makes up a project as a Zip file

- For any project, commands to

	- see what's pending (tasks etc)

	- suggest next steps

	- suggest ideas

## Model usage

Under a BYOK model I can add a number of LLM APIs for commercially available models as well as locally running instances (for example with Ollama) to be used in research, project execution, note-taking as well as links to open specific tools to configure the commands mentioned above.

Some of the commands above will need using the LLMs to actually power the feature or command

# Architecture

- Svelte, no Tailwind, try to use as little external dependencies as possible

- I would like the app to have actual pages, where the URL reflects a project name or ID so I can share or deeplink to a project

- FastAPI API protected by API Key

- PostgreSQL database combining SQL and NoSQL with JSONB for all the project artifacts we need. 

- .env file for all keys

- dockerize the solution on ports 7027 for the front and 7028 for the API

- use a persistent volume if needed to store anything so that things survive between restarts (for example pdfs and docx files used in projects as reference)

- Additionally, I want to create a google chrome extension that will allow me to select any text on any website, or save an URL to a specific project, for that the extension must be able to see into my projects so I can select which one I want to save the snippet or URL to. If that is not feasible with the local OS for security reasons, we will design a feature to have the list of projects reflected in cloud storage and read from and write to there.

	- the extension must rely on API endpoints specific to GET the project list and

	- POST an URL or snippet

# Methodology

Project must have unit tests to ensure we can create, edit etc all entities. 

All tests delete their data afterwards if they create anything in the database

Ask any questions you need to develop this tool
