### Readr

<div align="center">
  <p><em>A TUI that makes reading more enjoyable.</em></p>

  <p>
    <a href="https://github.com/DivyenduDutta/Atlas/blob/master/LICENSE"><img src="https://img.shields.io/github/license/DivyenduDutta/Atlas?style=flat-square" alt="License"></a>
  </p>

![CI](https://github.com/DivyenduDutta/Readr/actions/workflows/ci.yaml/badge.svg)

  <p>
    <a href="#introduction">Introduction</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#setup">Setup</a> •
    <a href="#quick-start">Quick Start</a> •
    <a href="#demo">Demo</a>
  </p>
</div>

## Introduction

Lorem Ipsum

## Architecture

Lorem Ipsum

## Setup

### UV

- Follow [this](https://docs.astral.sh/uv/getting-started/installation/) to install UV
- Install Python 3.12 using UV : `uv python install`
    - this will automatically pick up the correct python version for this project from `.python-version`
- Create a virtual environment : `uv venv`
- Build the project and install all dependencies : `uv sync --locked --all-extras --dev`

## Quick Start

### Sanity

Before committing changes run `uv run pre-commit run --all-files` or `uv run pre-commit run --file <file1>, <file2> ...`

### Run Readr

`uv run readr`
