from .spec import (
    Invalid,
    Spec,
    SpecBase,
    predicate,
    allof,
    anyof,
    seqof,
    mapof,
    keys,
    req,
    opt,
    inseq,
    any,


    valid,
    conform,
    explain
)

# renaming exports
# makes the API more intuitive by naming specs similar to python types
# handle exports here because it may interfere with other python code
from ghostwriter.utils.spec import spec as s
int = s.Int()
float = s.Float()
str = s.Str()
bool = s.Bool()
type = s.typ