from pyt.writer.writer import Writer
from io import StringIO
import yaml


def test_single_writer():
    # multiple indentation functions, single writer
    w = Writer(indent_by='    ')
    w.writeln("int foo = calcFoo();")
    w.writeln("")
    w.writeln("//we shall dance here")
    w.writeln_r("if (foo == 0) {")
    w.writeln("sayHello();")
    w.writeln_lr("} else if (foo < 100) {")
    w.writeln("sayGoodbye();")
    w.writeln_lr("} else {")
    w.writeln("sayAnything();")
    w.writeln_l("}")

    b = StringIO()
    w.render(b)
    actual = b.getvalue()
    expected = """\
int foo = calcFoo();

//we shall dance here
if (foo == 0) {
    sayHello();
} else if (foo < 100) {
    sayGoodbye();
} else {
    sayAnything();
}"""
    assert actual == expected, "code generation produces different output"


def test_advanced():
    # multiple indentation, multiple writers
    # uses a separate field writer to write fields together in one spot
    model_yml = """
    order:
        id: int
        customer_id: char
        date_of_purchase: datetime
    """
    model = yaml.load(model_yml)
    packagename = "org.example.acmecorp"

    def pascal_case(n):
        return "".join([s.capitalize() for s in n.split('_')])

    def camel_case(n):
        first, *rest = n.split('_')
        return first + "".join([
            s.capitalize() for s in rest
        ])

    def pojo_field(w, fw, field, typ):
        if typ == 'integer':
            typ = "int"
        elif typ == 'datetime':
            typ = "Datetime"
        elif typ == "char":
            typ = "String"
        ccField = camel_case(field)
        fw.writeln(f"{typ} {ccField};")
        w.writeln_r(f"public void {camel_case('set_' + field)}({typ} {ccField}) {{")
        w.writeln(f"this.{ccField} = {ccField};")
        w.writeln_l("}")
        w.writeln("")
        w.writeln_r(f"public {typ} {camel_case('get_' + field)}() {{")
        w.writeln(f"return this.{ccField};")
        w.writeln_l("}")

    w = Writer(indent_by='   ')
    w.writeln(f"package {packagename};")
    w.writeln("")
    for clazz in model.keys():
        w.writeln_r(f"public class {pascal_case(clazz)} " + "{")
        fw = w.section()
        for field, typ in model[clazz].items():
            w.writeln("")
            pojo_field(w, fw, field, typ)
    w.writeln_l("}")

    b = StringIO()
    w.render(b)
    actual = b.getvalue()
    print("code")
    print(actual)
    print("---")
    expected = """\
package org.example.acmecorp;

public class Order {
   int id;
   String customerId;
   Datetime dateOfPurchase;
   
   public void setId(int id) {
      this.id = id;
   }
   
   public int getId() {
      return this.id;
   }
   
   public void setCustomerId(String customerId) {
      this.customerId = customerId;
   }
   
   public String getCustomerId() {
      return this.customerId;
   }
   
   public void setDateOfPurchase(Datetime dateOfPurchase) {
      this.dateOfPurchase = dateOfPurchase;
   }
   
   public Datetime getDateOfPurchase() {
      return this.dateOfPurchase;
   }
}"""
    assert actual == expected, "code generation produces different output"
