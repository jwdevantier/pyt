# Why generate code ?
In most projects, there is some unique work, and a lot of boilerplate code.
Code-generation is excellent at reducing boilerplate code such as mapping objects to database tables, validating incoming data, memory allocation and deallocation functions and so on.

## Write simpler code
In general, programming languages often force you to trade code-size for complexity. Terse code often requires leveraging the most advanced aspects of your programming language. But can you justify the complexity? For example, your Python-colleagues probably understand decorators, but can you justify using meta-classes, dynamically generated code and the descriptor protocol in your quest to avoid bloating the code-base ?

## Decouple language and run-time
Another interesting point is that code-generation can decouple the language from the run-time. Using code generation, you can write high-level Python, but generate low-level C code for performance reasons, or generate Go code to create compact, performant microservices.
For an example of this approach, see [Outperforming everything with anything](https://wordsandbuttons.online/outperforming_everything_with_anything.html).

For Ghostwriter, I'm forcing you to use Python as that high-level, expressive language - but you are free to write your own code-generator ;)

## Transcend language boundaries
Code-generation is especially useful when concerns cross language boundaries. [gRPC](https://grpc.io/), for example, allows you to express a service's interface in IDL (interface definition language), which the gRPC code-generators read to generate those interfaces in a variety of programming languages.
In this way, the DRY principle is achieved by letting the IDL model be the single source of truth. Code-generators take care of providing the required client and server code, regardless of the implementation language.

Another good example is using code-generation to generate configuration-, docker files and more from a single model. In this way, synchronizing changes across various configuration formats becomes a breeze.

## More languages? More problems I say!
Increasingly, products span multiple languages. Many projects have started as a prototype in PHP and ended up with tens or hundreds of micro-services in a myriad of languages. Long-lived organizations will experience several technological shifts. Insisting on hiring PL/1, fortran or cobol programmers is just not sustainable, but neither is rewriting everything in the language of the day.

Language tradeoffs may lend them to certain use-cases while making them unfit for others; VM or machine-code ? Garbage collection or not? Static or dynamic typing? Functional or Object-oriented? Strict or lazy evaluation? Every choice matters.

Increasingly, the ecosystem *around* the language also matters. Python is arguably the preferred data-science and machine-learning language today because of its ecosystem of packages and projects supporting such tasks, which in turn begets even more libraries.

Finally, the run-time matters. Writing highly performant code in Python is harder than in Go and making Java FAAS programs start with the speed of Javascript requires extreme effort, possibly a different compiler and careful selection of libraries.

Using multiple languages certainly introduces some complexity, but making *one* language work for all use-cases and reinventing all the necessary libraries from other ecosystems is arguably more effort.


### Summary
* Reduce boilerplate without increasing complexity via leveraging advanced/opague language features
    * Generate objects from database schemas
    * Generate code for validating data or REST endpoints
* Avoid "expert" language features such as metaprogramming
* Learn one tool, leverage across languages
* Maintain consistent code across language boundaries
    * Example: [gRPC](https://grpc.io/)
* Decouple language and run-time
    * Write terse code in Python, generate for a fast runtime such as Go's VM
    * See blog post [Outperforming everything with anything](https://wordsandbuttons.online/outperforming_everything_with_anything.html)
