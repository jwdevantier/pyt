# Snippets

Snippets mark the regions of a file which contain generated code. Snippet syntax is loosely inspired by HTML in that there is a start- tag (e.g. `<@@my_module.my_snippet@@>`) and an end-tag (e.g. `<@@/my_module.my_snippet@@>`).
The content between the tags is the output from last executing the snippet.

## Snippets resolve to Python functions
Resolving a snippet name to a Python function closely follows the notation for regular imports. Thus the snippet:

```text
   <@@package1.package2.module.my_snippet@@>
   <@@/package1.package2.module.my_snippet@@>
```

... is roughly equivalent to the following in Python:

```python
from package1.package2.module import my_snippet
my_snippet(some_context, '   ', file_handle)
```

## Implementing snippets

***Note**: the raw snippet interface is very low-level - you will likely prefer using the [template DSL](template_dsl.md) which provides a convenient, high-level abstraction atop it. This interface is primarily exposed in case you want to build your own abstraction.*

Snippets are functions with the following signature:
```python
def my_snippet(ctx: Context, prefix: str, fw: IWriter):
    pass
```

* `context: Context`
    * Provides contextual information - the context object's scope/lifetime matches
    * `context.src`: The path of the file being processed
    * `context.env`: A dictionary in which you can store values. The values stored are available to all subsequent snippets in the file.
* `prefix: str`
    * Contains the leading whitespace (indentation) of the snippet opening line. Use `prefix` to indent each snippet line to match its context.
*  `fw: IWriter`
    * An interface allowing the snippet to write directly to the file via the `.write` method
    * The output overrides everything which was previously between the snippet's start- and end-tags
    * You are responsible for inserting newlines (`\n`) and using `prefix` to properly indent lines

Assuming the `my_snippet` implementation is this:

```python
def my_snippet(ctx: Context, prefix: str, fw: IWriter):
    fw.write(f"{prefix}hello")
    fw.write(", world!\n")
    fw.write("something else")
```

The final output in the file would be:
```text
   <@@package1.package2.module.my_snippet@@>
   hello, world!
something else
   <@@/package1.package2.module.my_snippet@@>
```


## Where to store the snippet code
Ghostwriter uses the standard Python import mechanism to locate snippet functions. Chiefly, Python uses the list of directories in `sys.path` to determine which directories to search and in what order when handling imports. Any directories added to the `search_paths` list in the configuration file are automatically appended to the standard list.
