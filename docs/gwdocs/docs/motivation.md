# Motivation

## Writing reusable code is hard
Programming languages often force you to trade code-size for complexity. The most complex features of a
programming language typically lend themselves to reducing repetition. From functors in Ocaml to generics
in C#, metaclasses in Python, macros in Lisp or implementing code-generation based on annotations in Java.

Even if intimately familiar with these features, can you justify their complexity? Liberally using these features will create code which not all colleagues can follow or extend in meaningful ways. 

On top of this, most organizations use multiple languages. Mastering the features of all to write reusable code becomes harder still. Additionally, while some organizations have internal package repositories, few
have them for all languages used in the organization, so sharing code across projects becomes problematic. Writing and distributing reusable code is a hard problem.

## Code is liability
On the other hand, writing reams of "simple", repetitive code presents, in addition to boredom, another issue: [code is a liability, not an asset](https://wiki.c2.com/?SoftwareAsLiability). As code-bases grow, it becomes harder to grasp the overall architecture and correctly refactoring code to keep the program maintainable in face of changing requirements becomes increasingly expensive. As a result, the architecture tends to deterioate as quick fixes and features breaking the previous design are piled on.


## Repetition in config files and provisioning tools
But writing reusable code is not the only challenge. Increasingly, various DSL's and configuration systems are
also used. In order to avoid repeating yourself, do you know how to:

* Use anchors in YAML configuration files?
* Use multiple docker-compose files to make several environments share a common base or how to best leverage `docker-compose.override.yml` to tweak a configuration for your local setup?
* Write reusable Terraform modules? Have you experiences some of the pitfalls and limitations of modules and do you know how to work around them (if possible?)
* Lay out Ansible projects to maximize reuse of code and playbooks?
    * E.g. how to write filters, custom modules, writing reusable playbooks, expressing (parametrized?) dependencies among playbooks etc
* In `Dockerfile`'s, can you use `ARG` and `ONBUILD` etc to create highly customizable base images?

## Summary
* Reusable code typically leverages advanced language features
    * May be hard to understand for junior engineers or those unfamiliar with the language
* Organizations tend to accumulate languages and frameworks over their lifetime
    * More code to manage - more languages to master
* Distributing reusable code is also hard
    * Requires infrastructure for language-specific package repositories
* Multiple configuration tools and DSL's in use
    * Do you grasp and exploit the features each provide to keep things DRY?

Writing reams of repetitive code or configuration files is no panacea. More code to reason about, meaning changes by newcomers are more likely to violate the overall architecture. Wide-scale refactoring to improve software maintainability becomes more unlikely.