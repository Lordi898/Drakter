# shadcn

Copy Page

[Previous](/docs/dark-mode)[Next](/docs/monorepo)

Use the shadcn CLI to add components to your project.

## init

Use the `init` command to initialize configuration and dependencies for a new project.

The `init` command installs dependencies, adds the `cn` util and configures CSS variables for the project.
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest init

Copy

**Options**
    
    
    CopyUsage: shadcn init [options] [components...]
     
    initialize your project and install dependencies
     
    Arguments:
      components         name, url or local path to component
     
    Options:
      -t, --template <template>      the template to use. (next, next-monorepo)
      -b, --base-color <base-color>  the base color to use. (neutral, gray, zinc, stone, slate)
      -y, --yes                      skip confirmation prompt. (default: true)
      -f, --force                    force overwrite of existing configuration. (default: false)
      -c, --cwd <cwd>                the working directory. defaults to the current directory.
      -s, --silent                   mute output. (default: false)
      --src-dir                      use the src directory when creating a new project. (default: false)
      --no-src-dir                   do not use the src directory when creating a new project.
      --css-variables                use css variables for theming. (default: true)
      --no-css-variables             do not use css variables for theming.
      --no-base-style                do not install the base shadcn style
      -h, --help                     display help for command

* * *

## add

Use the `add` command to add components and dependencies to your project.
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add [component]

Copy

**Options**
    
    
    CopyUsage: shadcn add [options] [components...]
     
    add a component to your project
     
    Arguments:
      components         name, url or local path to component
     
    Options:
      -y, --yes           skip confirmation prompt. (default: false)
      -o, --overwrite     overwrite existing files. (default: false)
      -c, --cwd <cwd>     the working directory. defaults to the current directory.
      -a, --all           add all available components (default: false)
      -p, --path <path>   the path to add the component to.
      -s, --silent        mute output. (default: false)
      --src-dir           use the src directory when creating a new project. (default: false)
      --no-src-dir        do not use the src directory when creating a new project.
      --css-variables     use css variables for theming. (default: true)
      --no-css-variables  do not use css variables for theming.
      -h, --help          display help for command

* * *

## view

Use the `view` command to view items from the registry before installing them.
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest view [item]

Copy

You can view multiple items at once:
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest view button card dialog

Copy

Or view items from namespaced registries:
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest view @acme/auth @v0/dashboard

Copy

**Options**
    
    
    CopyUsage: shadcn view [options] <items...>
     
    view items from the registry
     
    Arguments:
      items            the item names or URLs to view
     
    Options:
      -c, --cwd <cwd>  the working directory. defaults to the current directory.
      -h, --help       display help for command

* * *

## search

Use the `search` command to search for items from registries.
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest search [registry]

Copy

You can search with a query:
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest search @shadcn -q "button"

Copy

Or search multiple registries at once:
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest search @shadcn @v0 @acme

Copy

The `list` command is an alias for `search`:
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest list @acme

Copy

**Options**
    
    
    CopyUsage: shadcn search|list [options] <registries...>
     
    search items from registries
     
    Arguments:
      registries             the registry names or urls to search items from. Names
                             must be prefixed with @.
     
    Options:
      -c, --cwd <cwd>        the working directory. defaults to the current directory.
      -q, --query <query>    query string
      -l, --limit <number>   maximum number of items to display per registry (default: "100")
      -o, --offset <number>  number of items to skip (default: "0")
      -h, --help             display help for command

* * *

## list

Use the `list` command to list all items from a registry.
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest list @acme

Copy

**Options**
    
    
    CopyUsage: shadcn list [options] <registries...>
     
    list items from registries
     
    Arguments:
      registries             the registry names or urls to list items from. Names
        must be prefixed with @.

**Options**
    
    
    CopyUsage: shadcn list [options] <registries...>
     
    list items from registries
     
    Arguments:
      registries             the registry names or urls to list items from. Names
        must be prefixed with @.

* * *

## build

Use the `build` command to generate the registry JSON files.
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest build

Copy

This command reads the `registry.json` file and generates the registry JSON files in the `public/r` directory.

**Options**
    
    
    CopyUsage: shadcn build [options] [registry]
     
    build components for a shadcn registry
     
    Arguments:
      registry             path to registry.json file (default: "./registry.json")
     
    Options:
      -o, --output <path>  destination directory for json files (default: "./public/r")
      -c, --cwd <cwd>      the working directory. defaults to the current directory.
      -h, --help           display help for command

To customize the output directory, use the `--output` option.
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest build --output ./public/registry

Copy

[ Dark Mode](/docs/dark-mode)[Monorepo ](/docs/monorepo)
