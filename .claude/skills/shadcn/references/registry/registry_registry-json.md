# registry.json

Copy Page

[Previous](/docs/registry/open-in-v0)[Next](/docs/registry/registry-item-json)

Schema for running your own component registry.

The `registry.json` schema is used to define your custom component registry.

registry.json
    
    
    Copy{
      "$schema": "https://ui.shadcn.com/schema/registry.json",
      "name": "shadcn",
      "homepage": "https://ui.shadcn.com",
      "items": [
        {
          "name": "hello-world",
          "type": "registry:block",
          "title": "Hello World",
          "description": "A simple hello world component.",
          "registryDependencies": [
            "button",
            "@acme/input-form",
            "https://example.com/r/foo"
          ],
          "dependencies": ["is-even@3.0.0", "motion"],
          "files": [
            {
              "path": "registry/new-york/hello-world/hello-world.tsx",
              "type": "registry:component"
            }
          ]
        }
      ]
    }

## Definitions

You can see the JSON Schema for `registry.json` [here](https://ui.shadcn.com/schema/registry.json).

### $schema

The `$schema` property is used to specify the schema for the `registry.json` file.

registry.json
    
    
    Copy{
      "$schema": "https://ui.shadcn.com/schema/registry.json"
    }

### name

The `name` property is used to specify the name of your registry. This is used for data attributes and other metadata.

registry.json
    
    
    Copy{
      "name": "acme"
    }

### homepage

The homepage of your registry. This is used for data attributes and other metadata.

registry.json
    
    
    Copy{
      "homepage": "https://acme.com"
    }

### items

The `items` in your registry. Each item must implement the [registry-item schema specification](https://ui.shadcn.com/schema/registry-item.json).

registry.json
    
    
    Copy{
      "items": [
        {
          "name": "hello-world",
          "type": "registry:block",
          "title": "Hello World",
          "description": "A simple hello world component.",
          "registryDependencies": [
            "button",
            "@acme/input-form",
            "https://example.com/r/foo"
          ],
          "dependencies": ["is-even@3.0.0", "motion"],
          "files": [
            {
              "path": "registry/new-york/hello-world/hello-world.tsx",
              "type": "registry:component"
            }
          ]
        }
      ]
    }

See the [registry-item schema documentation](/docs/registry/registry-item-json) for more information.

[ Open in v0](/docs/registry/open-in-v0)[registry-item.json ](/docs/registry/registry-item-json)
