import pytest
from ghostwriter.utils.fhash import file_hash

file1_contents = """\
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
"""
file1_hash = "864778486c2a58bfd2041cea3f95a9ab"


@pytest.mark.usefixtures("tmpfile")
@pytest.mark.parametrize("contents", [
    file1_contents,
])
def test_file_hash_algorithm_is_stable(tmpfile, contents):
    with tmpfile("w", encoding='utf8') as input_contents:
        input_contents.write(contents)
        input_contents.flush()
        input_fname = input_contents.name
    print(f"wrote to '{input_fname}'")

    with open(input_fname, mode='r', encoding='utf8') as fh:
        disk_contents = fh.read()
    assert file1_contents == disk_contents, "written contents deviate from input"
    assert file_hash(input_fname) == file_hash(input_fname), "expected hashing output to be stable"


@pytest.mark.usefixtures("tmpfile")
@pytest.mark.parametrize("contents, md5sum", [
    (file1_contents, file1_hash)
])
def test_same_contents_same_hash(tmpfile, contents, md5sum):
    with tmpfile("w", encoding='utf8') as fileA:
        fileA.write(contents)
        fileA.flush()
        file_a_path = fileA.name
    with tmpfile("w", encoding='utf8') as fileB:
        fileB.write(contents)
        fileB.flush()
        file_b_path = fileB.name

    with open(file_a_path, mode='r', encoding='utf8') as fh_file_a:
        with open(file_b_path, mode='r', encoding='utf8') as fh_file_b:
            file_a_disk_contents = fh_file_a.read()
            file_b_disk_contents = fh_file_b.read()
    assert file_a_disk_contents != "", "file A is unexpectedly empty!"
    assert file_b_disk_contents != "", "file B is unexpectedly empty!"

    assert file_a_disk_contents == file_b_disk_contents, "contents of the two files should be identical"

    assert file_hash(file_a_path) == file_hash(file_b_path), "expected hashes of identical files to be identical"


@pytest.mark.usefixtures("tmpfile")
@pytest.mark.parametrize("contents, md5sum", [
    (file1_contents, file1_hash)
])
def test_file_hash_matches_md5sum(tmpfile, contents, md5sum):
    with tmpfile("w", encoding='utf8') as input_contents:
        input_contents.write(contents)
        input_contents.flush()
        input_fname = input_contents.name
    print(f"wrote to '{input_fname}'")

    with open(input_fname, mode='r', encoding='utf8') as fh:
        disk_contents = fh.read()
    assert file1_contents == disk_contents, "written contents deviate from input"
    assert md5sum == file_hash(input_fname), "computed hash deviates from expected"
