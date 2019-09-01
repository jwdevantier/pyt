# Why generate code ?
In most projects, there is some unique work, and a lot of boilerplate code.
Code-generation is excellent at reducing boilerplate code such as mapping objects to database tables, validating incoming data on REST interfaces, memory allocation and deallocation functions and so on.

In general, programming languages often you to trade code-size for complexity. Terse code often requires leveraging the most advanced aspects of your programming language. But can you justify the complexity? For example, your Python-colleagues probably understand decorators, but can you justify using meta-classes, dynamically generated code and the descriptor protocol in your quest to avoid bloating the code-base ?

Increasingly, products also span multiple languages. Many projects has started as a prototype in PHP and ended up with tens or hundreds of micro-services in a myriad of languages. Also, some use-cases almost mandate a particular language, such as Javascript for the web or Python for machine-learning.
In all these cases, standardizing on a code-generator can enable writing less code without leveraging the most esoteric aspects of a language, and it is almost required in cases where concerns cross language boundaries.
Consider gRPC, an increasingly popular alternative to REST in microservices architectures. With gRPC, the interface boundary between server and client is expressed in an IDL (interface definition language) file from which server and client code is generated in any number of languages.

Another interesting point is that code-generation can decouple the language from the run-time. Using code generation, you can write high-level Python, but generate low-level C code for performance reasons, or generate Go code to create compact, performant microservices.

Finally, yes, code-generation itself introduces some complexity, but consider that products are increasingly leveraging multiple languages. Whether because some languages are near-mandatory for some use-cases (Python for machine-learning, Javascript for the web), acquisitions or expertise across the organization, standardizing on just one language rarely happens.
In this case, code-generation can both reduce the need to leverage each language's most advanced features for code-reuse and help generating consistent interfaces between the languages, as is the case with gRPC where IDL models generate interfaces in Go, Python, Java or something else.

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
