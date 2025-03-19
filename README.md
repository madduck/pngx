# pngx — a CLI tool to interact with Paperless-NGX

This command-line tool exists to facilitate interaction with the [Paperless-NGX DMS](https://docs.paperless-ngx.com/). It uses the [PyPaperless](https://pypi.org/project/pypaperless/) API client to do the heavy lifting.

This tool is work in progress, and I will add functionality as I need it. Feel free to open pull requests if you need something, should be relatively easy to add the glue between the [click](https://click.palletsprojects.com/) library, and the API client.

## Call for help — uploading to PyPi

I would love to publish this to [PyPi](https://pypi.org/), but I don't know how. So if someone could set up a CI pipeline on Github for me, or help me do this, that would be great!

## Installation

The recommended way to install `pngx` is using a virtual environment for now. I personally love using [direnv](https://direnv.net/) for this:

```bash
mkdir ~/code/pngx
cd ~/code/pngx

echo layout python3 > .envrc
direnv allow .

git clone https://github.com/madduck/pngx
cd pngx

pip install -e .

pngx …
```

Now, to run, you need to switch to the directory:

```bash
(~/code/pngx && pngx …)
```

Alternatively, if you have a custom `bin` directory in your `$PATH`, then add a symlink there (I trust you'll amend the paths accordingly):

```bash
cd ~/bin
ln -s ../code/pngx/.direnv/*/bin/pngx
cd

pngx …
```

## Usage

```
$ pngx --help

Usage: pngx [OPTIONS] COMMAND [ARGS]...

  A command-line interface for Paperless NGX

Options:
  -U, --url TEXT     URL to the Paperless NGX instance
  -T, --token TEXT   API token for Paperless NGX instance
  -c, --config PATH  Config file to read
  -v, --verbose      Increase verbosity of log output
  -q, --quiet        Increase verbosity of log output
  --help             Show this message and exit.

Commands:
  tags
  upload
```

Instead of providing URL and API token with each call, you can also create a configuration file (default: `$XDG_CONFIG_DIR/pngx/config`) like so:

```
url = "https://dms.example.org"
token = "3382e1ff8ef2cca83f8385a09b93d61c82fe4a4a"

[upload]
tags_must_exist = true
```

### Uploading files

```
$ pngx upload --help
Usage: pngx upload [OPTIONS] [FILENAMES]...

  Upload files to Paperless NGX

Options:
  -o, --owner TEXT            Owner for uploaded documents
  -g, --group TEXT            Groups for uploaded documents
  -t, --tag TEXT              Tags to assign to the documents
  -x, --tags-must-exist       Tags will not be created, but an error produced
                              if a tag does not exist
  --replace-with-spaces TEXT  Characters in filenames to replace with spaces
  --datere TEXT               Python regular expressions to extract date
  --tries INTEGER RANGE       Retry this many times to upload documents
                              [x>=1]
  --help                      Show this message and exit.
```

### Handling tags

```
$ pngx tags --help
Usage: pngx tags [OPTIONS] COMMAND [ARGS]...

  Commands to manipulate tags in Paperless NGX

Options:
  --help  Show this message and exit.

Commands:
  list
```

#### Listing tags

```
$ pngx tags list --help
Usage: pngx tags list [OPTIONS]

  List the available tags in Paperless NGX

Options:
  -0, --zero  Use zero-delimiter instead of newlines
  --help      Show this message and exit.
```

## Legalese

`pngx` is © 2025 martin f. krafft <pngx@pobox.madduck.net>.

It is released under the terms of the MIT Licence.
