# JavaScript

Copy Page

[Previous](/docs/v0)[Next](/docs/blocks)

How to use shadcn/ui with JavaScript

This project and the components are written in TypeScript. We recommend using TypeScript for your project as well.

However we provide a JavaScript version of the components as well. The JavaScript version is available via the [cli](/docs/cli).

To opt-out of TypeScript, you can use the `tsx` flag in your `components.json` file.

components.json
    
    
    Copy{
      "style": "new-york",
      "rsc": false,
      "tsx": false,
      "tailwind": {
        "config": "",
        "css": "src/app/globals.css",
        "baseColor": "zinc",
        "cssVariables": true
      },
      "iconLibrary": "lucide",
      "aliases": {
        "components": "@/components",
        "utils": "@/lib/utils",
        "ui": "@/components/ui",
        "lib": "@/lib",
        "hooks": "@/hooks"
      }
    }

To configure import aliases, you can use the following `jsconfig.json`:

jsconfig.json
    
    
    Copy{
      "compilerOptions": {
        "paths": {
          "@/*": ["./*"]
        }
      }
    }

[ Open in v0](/docs/v0)[Blocks ](/docs/blocks)

Deploy your shadcn/ui app on Vercel

Trusted by OpenAI, Sonos, Adobe, and more.

Vercel provides tools and infrastructure to deploy apps and features at scale.

Deploy Now[Deploy to Vercel](https://vercel.com/new?utm_source=shadcn_site&utm_medium=web&utm_campaign=docs_cta_deploy_now_callout)

Built by [shadcn](https://twitter.com/shadcn) at [Vercel](https://vercel.com/new?utm_source=shadcn_site&utm_medium=web&utm_campaign=docs_cta_deploy_now_callout). The source code is available on [GitHub](https://github.com/shadcn-ui/ui).
