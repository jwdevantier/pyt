# How it works
Ghostwriter essentially allows you to embed bits of generated code among regular, hand-written code. To do this,
Ghostwriter parses your files, looking for special comments marking the start and end of a section of generated code. These sections are called **snippets**. Each snippet has a name, e.g. `gen.api.customer_resource` which is resolved to a Python function.
The function is then called and is able to write to this section of the file marked by the start and end of the snippet.
Each time a file is compiled, it is copied line-by-line, except the snippet sections, whose contents is replaced by running the snippet functions again.

To avoid having to manually recompile files, Ghostwriter will monitor (watch) your project, automatically recompiling files as they change. This way you can split your editor view, make changes to the code-generator parts and see the changes reflected immediately in the output file.

The code used for code-generation is organized as a regular Python project. This means you can get full editor support, install community libraries with pip, write unit tests and so on. Ghostwriter simply leverages the excellent community of Python to enable you to draw data from yaml, databases or anything else which Python can speak to.

Ghostwriter introduces 3 ways to generate code. The basic snippet abstraction lets your write characters, `print()`-style, directly into the file (bring your own newlines!). The [writer](writer.md) interface, which abstracts issues of indentation and supports editing in multiple places at the same time. The [template](template_dsl.md) language goes further still, offering a full, extensible templating language with [React-like](https://reactjs.org) components.
Finally, you can of build your own code-generation method atop the basic snippet interface.
