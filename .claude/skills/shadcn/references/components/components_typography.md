# Typography

Copy Page

[Previous](/docs/components/tooltip)[Next](/docs/forms)

Styles for headings, paragraphs, lists...etc

We do not ship any typography styles by default. This page is an example of how you can use utility classes to style your text.

# Taxing Laughter: The Joke Tax Chronicles

Once upon a time, in a far-off land, there was a very lazy king who spent all day lounging on his throne. One day, his advisors came to him with a problem: the kingdom was running out of money.

## The King's Plan

The king thought long and hard, and finally came up with a brilliant plan: he would tax the jokes in the kingdom.

> "After all," he said, "everyone enjoys a good joke, so it's only fair that they should pay for the privilege."

### The Joke Tax

The king's subjects were not amused. They grumbled and complained, but the king was firm:

  * 1st level of puns: 5 gold coins
  * 2nd level of jokes: 10 gold coins
  * 3rd level of one-liners : 20 gold coins

As a result, people stopped telling jokes, and the kingdom fell into a gloom. But there was one person who refused to let the king's foolishness get him down: a court jester named Jokester.

### Jokester's Revolt

Jokester began sneaking into the castle in the middle of the night and leaving jokes all over the place: under the king's pillow, in his soup, even in the royal toilet. The king was furious, but he couldn't seem to stop Jokester.

And then, one day, the people of the kingdom discovered that the jokes left by Jokester were so funny that they couldn't help but laugh. And once they started laughing, they couldn't stop.

### The People's Rebellion

The people of the kingdom, feeling uplifted by the laughter, started to tell jokes and puns again, and soon the entire kingdom was in on the joke.

King's Treasury| People's happiness  
---|---  
Empty| Overflowing  
Modest| Satisfied  
Full| Ecstatic  
  
The king, seeing how much happier his subjects were, realized the error of his ways and repealed the joke tax. Jokester was declared a hero, and the kingdom lived happily ever after.

The moral of the story is: never underestimate the power of a good laugh and always be careful of bad ideas.

## h1

# Taxing Laughter: The Joke Tax Chronicles

Copy
    
    
    export function TypographyH1() {
      return (
        <h1 className="scroll-m-20 text-center text-4xl font-extrabold tracking-tight text-balance">
          Taxing Laughter: The Joke Tax Chronicles
        </h1>
      )
    }
    

## h2

## The People of the Kingdom

Copy
    
    
    export function TypographyH2() {
      return (
        <h2 className="scroll-m-20 border-b pb-2 text-3xl font-semibold tracking-tight first:mt-0">
          The People of the Kingdom
        </h2>
      )
    }
    

## h3

### The Joke Tax

Copy
    
    
    export function TypographyH3() {
      return (
        <h3 className="scroll-m-20 text-2xl font-semibold tracking-tight">
          The Joke Tax
        </h3>
      )
    }
    

## h4

#### People stopped telling jokes

Copy
    
    
    export function TypographyH4() {
      return (
        <h4 className="scroll-m-20 text-xl font-semibold tracking-tight">
          People stopped telling jokes
        </h4>
      )
    }
    

## p

The king, seeing how much happier his subjects were, realized the error of his ways and repealed the joke tax.

Copy
    
    
    export function TypographyP() {
      return (
        <p className="leading-7 [&:not(:first-child)]:mt-6">
          The king, seeing how much happier his subjects were, realized the error of
          his ways and repealed the joke tax.
        </p>
      )
    }
    

## blockquote

> "After all," he said, "everyone enjoys a good joke, so it's only fair that they should pay for the privilege."

Copy
    
    
    export function TypographyBlockquote() {
      return (
        <blockquote className="mt-6 border-l-2 pl-6 italic">
          &quot;After all,&quot; he said, &quot;everyone enjoys a good joke, so
          it&apos;s only fair that they should pay for the privilege.&quot;
        </blockquote>
      )
    }
    

## table

King's Treasury| People's happiness  
---|---  
Empty| Overflowing  
Modest| Satisfied  
Full| Ecstatic  
  
Copy
    
    
    export function TypographyTable() {
      return (
        <div className="my-6 w-full overflow-y-auto">
          <table className="w-full">
            <thead>
              <tr className="even:bg-muted m-0 border-t p-0">
                <th className="border px-4 py-2 text-left font-bold [&[align=center]]:text-center [&[align=right]]:text-right">
                  King&apos;s Treasury
                </th>
                <th className="border px-4 py-2 text-left font-bold [&[align=center]]:text-center [&[align=right]]:text-right">
                  People&apos;s happiness
                </th>
              </tr>
            </thead>
            <tbody>
              <tr className="even:bg-muted m-0 border-t p-0">
                <td className="border px-4 py-2 text-left [&[align=center]]:text-center [&[align=right]]:text-right">
                  Empty
                </td>
                <td className="border px-4 py-2 text-left [&[align=center]]:text-center [&[align=right]]:text-right">
                  Overflowing
                </td>
              </tr>
              <tr className="even:bg-muted m-0 border-t p-0">
                <td className="border px-4 py-2 text-left [&[align=center]]:text-center [&[align=right]]:text-right">
                  Modest
                </td>
                <td className="border px-4 py-2 text-left [&[align=center]]:text-center [&[align=right]]:text-right">
                  Satisfied
                </td>
              </tr>
              <tr className="even:bg-muted m-0 border-t p-0">
                <td className="border px-4 py-2 text-left [&[align=center]]:text-center [&[align=right]]:text-right">
                  Full
                </td>
                <td className="border px-4 py-2 text-left [&[align=center]]:text-center [&[align=right]]:text-right">
                  Ecstatic
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )
    }
    

## list

  * 1st level of puns: 5 gold coins
  * 2nd level of jokes: 10 gold coins
  * 3rd level of one-liners : 20 gold coins

Copy
    
    
    export function TypographyList() {
      return (
        <ul className="my-6 ml-6 list-disc [&>li]:mt-2">
          <li>1st level of puns: 5 gold coins</li>
          <li>2nd level of jokes: 10 gold coins</li>
          <li>3rd level of one-liners : 20 gold coins</li>
        </ul>
      )
    }
    

## Inline code

`@radix-ui/react-alert-dialog`

Copy
    
    
    export function TypographyInlineCode() {
      return (
        <code className="bg-muted relative rounded px-[0.3rem] py-[0.2rem] font-mono text-sm font-semibold">
          @radix-ui/react-alert-dialog
        </code>
      )
    }
    

## Lead

A modal dialog that interrupts the user with important content and expects a response.

Copy
    
    
    export function TypographyLead() {
      return (
        <p className="text-muted-foreground text-xl">
          A modal dialog that interrupts the user with important content and expects
          a response.
        </p>
      )
    }
    

## Large

Are you absolutely sure?

Copy
    
    
    export function TypographyLarge() {
      return <div className="text-lg font-semibold">Are you absolutely sure?</div>
    }
    

## Small

Email address

Copy
    
    
    export function TypographySmall() {
      return (
        <small className="text-sm leading-none font-medium">Email address</small>
      )
    }
    

## Muted

Enter your email address.

Copy
    
    
    export function TypographyMuted() {
      return (
        <p className="text-muted-foreground text-sm">Enter your email address.</p>
      )
    }
    

[ Tooltip](/docs/components/tooltip)[Forms ](/docs/forms)
