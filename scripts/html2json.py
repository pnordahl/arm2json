"""
    html2json.py
    by Dima Kovalenko
"""

from lxml.html import fromstring
import os
import re
import json
import datetime
import sys


class XHTMLParser:

    def __init__(self, xhtml_path, json_path):
        # Initialisation
        self.encodings = []
        # Does the folder exist?
        full_xhtml_path = os.path.realpath(xhtml_path)
        print "Try %s..." % xhtml_path
        if not os.path.isdir(xhtml_path):
            print "The first argument must be a path to xhtm folder!"
            exit()
        # Loop html files in the folder
        for file_name in os.listdir(xhtml_path):
            instruction = self.get_instruction(os.path.join(full_xhtml_path, file_name), file_name)
            if instruction is not None:
                print "Processing %s..." % file_name
                self.encodings.append(instruction)
        # Try to save the result to JSON
        if len(self.encodings) > 0:
            full_json_path = os.path.realpath(json_path)
            print "Generating %s..." % full_json_path
            result = {
                "generated_from": xhtml_path,
                "time": str(datetime.datetime.now()),
                "encodings": self.encodings
            }
            try:
                f = open(full_json_path, "w")
                f.write(json.dumps(result, indent=4))
                f.close()
            except IOError:
                print "Can't create %s" % full_json_path
        else:
            # No instruction html found :(
            print "Nothing was processed, probably you specified a wrong xhtml folder"

    @staticmethod
    def get_fields(regdiagram, file_name):
        # Initial values
        fields = {}
        pos = 31
        # Init masks
        mask = ""
        mask_sign = ""
        # Get the first row
        first_row = regdiagram.xpath("table/tbody/tr[@class='firstrow']/td")
        # Loot the first row
        for block in first_row:
            # Get field name or value
            field_name = block.text if block.text is not None else ""
            # Get field length
            colspan = block.get("colspan")
            length = int(colspan) if colspan is not None else 1
            # Check field name or value
            if not (re.match(r"[!= ]{0,3}[x01]+", field_name) or field_name == ""):
                # It's  a name, e.g. op0
                fields[field_name] = {"hi": pos, "lo": pos - length + 1, "value": "x"*length, "equal": "=="}
                mask += "x"*length
                mask_sign += "="*length
            else:
                # It's a value, e.g. !=0x1...
                mask += field_name.replace("!=", "").strip()
                mask_sign += ("!" if field_name.startswith("!=") else "=")*length
            pos = pos - length
        # Reverte mask
        mask = mask[::-1]
        mask_sign = mask_sign[::-1]
        # Find the second row
        second_row = regdiagram.xpath("table/tbody/tr[@class='secondrow']/td")
        # If the second row found, ...
        if len(second_row) > 0:
            # ...loop it
            pos = 31
            for block in second_row:
                # Get field name (there are no values in the second row)
                field_name = block.text
                # Get field length
                colspan = block.get("colspan")
                length = int(colspan) if colspan is not None else 1
                # If the field name is not empty...
                if field_name != "" and field_name is not None:
                    # ...get value and "==" or "!=" from mask and mask_sign correspondingly
                    value = mask[pos-length + 1:pos + 1][::-1]
                    equal = mask_sign[pos-length + 1: pos + 1]
                    # It's impossible to have "!=" and "==" at the same time! Make a check:
                    if "!" in equal and "=" in equal:
                        print "Error! Fail to parse second row in the regdiagram: %s in %s" % (regdiagram, file_name)
                        exit()
                    # Add the field to the fields:
                    fields[field_name] = {
                        "hi": pos, "lo": pos - length + 1, "value": value, "equal": "==" if "=" in equal else "!="
                    }
                # Correct the position
                pos = pos - length
        # Return the collected fields
        return fields

    @staticmethod
    def get_masks(regdiagram):
        # Init 'equal' and 'uneqal' mask(s)
        eq_mask = ""
        uneq_masks = []
        # Find the first row
        first_row = regdiagram.xpath("table/tbody/tr[@class='firstrow']/td")
        # Initial position
        pos = 31
        # Loop the first row
        for block in first_row:
            # Get value
            block_value = block.text if block.text is not None else ""
            # Get length
            colspan = block.get("colspan")
            length = int(colspan) if colspan is not None else 1
            # If its not !=01x... or 01x..., then add "x" (length times) to the equal mask
            if not re.match("[!= ]{0,3}[x01]+", block_value):
                eq_mask += "x" * length
            else:
                # Else, manage cases !=10x... and 10x...
                if block_value.startswith("!="):
                    eq_mask += "x" * length
                    uneq_masks.append("x" * (31 - pos) + block_value.replace("!= ", "").strip() + "x" * (pos - length + 1))
                else:
                    eq_mask += block_value.strip()
            # Correct the length
            pos = pos - length
        # Check masks (by length)
        if len(eq_mask) != 32:
            print "Error! %s mask is not 32 bits length!" % eq_mask
            exit()
        for m in uneq_masks:
            if len(m) != 32:
                print "Error! %s mask is not 32 bits length!" % m
                exit()
        # Return the masks
        return eq_mask, uneq_masks if len(uneq_masks) > 0 else None

    @staticmethod
    def get_arch(something):
        # Get arch -- find <fond style="font-size:smaller"> ...</font>
        arch = something.xpath("font[@style='font-size:smaller;']")
        # Found?
        if arch is not None and len(arch) > 0:
            # Yes! Return the internal text without spaces and \n
            arch = re.sub(r'[ \n\)\(]', "", arch[0].text_content())
        else:
            # No
            arch = None
        # Return the architecture!
        return arch

    @staticmethod
    def get_encodings(regdiagram):
        # Get next <div class="encoding">...</div> and <div class="regdiagram-32">...</div>
        all_encodings = regdiagram.xpath("./following-sibling::div[@class='encoding' or @class='regdiagram-32']")
        # Filter the results, remain only the <div class="encoding">...</div>
        # before the next <div class="regdiagram-32">...</div>
        encodings = []
        for enc in all_encodings:
            if enc.get("class") != "regdiagram-32":
                encodings.append(enc)
            else:
                break
        # Initialise the result
        result = []
        # Loop the encodings
        for enc in encodings:

            h4 = enc.xpath("h4[@class='encoding']")[0]
            title = h4.text
            bitdif = h4.xpath("span[@class='bitdiff']")
            if bitdif is not None and len(bitdif) > 0:
                bitdif = bitdif[0].text.strip()
            else:
                bitdif = None
            arch = XHTMLParser.get_arch(h4)
            asm = enc.xpath("p[@class='asm-code']")[0].text_content()
            result.append({"title": title, "arch": arch, "bitdiff": bitdif, "asm": asm})
        return result

    @staticmethod
    def arrange_text(indent, width, text):
        # Make the text indented and set the text width
        words = text.split(" ")
        arranged = " " * indent
        length = len(arranged)
        for w in words:
            length += len(w) + 1
            if length < width:
                arranged += w + " "
            else:
                prefix = "\n" + " " * indent + w + " "
                arranged += prefix
                length = len(prefix) - 1
        return arranged

    @staticmethod
    def get_instruction_description(root):
        # Collect all p, ul, and <div class="regdiagram-32">
        h2 = root.xpath("h2[@class='instruction-section']")[0]
        description = h2.xpath(
            "./following-sibling::p | ./following-sibling::ul | ./following-sibling::div[@class='regdiagram-32']"
        )
        # Cut the list to description onlu
        for i in range(len(description)):
            if description[i].get("class") == "regdiagram-32":
                description = description[:i]
                break
        text = ""
        for entry in description:
            # Process <p>...</p>
            if entry.tag == "p":
                text_to_add = re.sub(r'[\n\t]+', " ", entry.text_content())
                text_to_add = re.sub(r'[ ]{2,}', " ", text_to_add)
                text_to_add = XHTMLParser.arrange_text(0, 80, text_to_add.strip())
                text += text_to_add + "\n\n"
            # Process a list
            elif entry.tag == "ul":
                li = entry.xpath("li")
                for item in li:
                    text_to_add = re.sub(r'[\n\t]+', " ", item.text_content())
                    text_to_add = re.sub(r'[ ]{2,}', " ", text_to_add)
                    text_to_add = XHTMLParser.arrange_text(2, 80, text_to_add.strip())
                    text_to_add = "* " + text_to_add[2:]
                    text += text_to_add + "\n"
        # Return the final test
        return text.strip()

    def get_aliases(self, root, file_name):
        # Get the alias table (if any)
        alias_table = root.xpath("table[@class='aliastable']")
        if len(alias_table) == 0:
            return None
        if len(alias_table) > 1:
            print "Error! Must me the only alias table in %s" % file_name
            exit()
        # Mine links from the alias table
        links = []
        for a in alias_table[0].xpath("tbody/tr/td/a"):
            href = a.get("href")
            if href not in links:
                links.append(href.replace(".html", ""))
        return links

    def get_instruction(self, full_path_to_file, file_name):
        if full_path_to_file.endswith(".html"):
            # Parse another html file with lxml
            file_handler = open(full_path_to_file, "r")
            root = fromstring(file_handler.read()).xpath("/html/body")[0]
            file_handler.close()
            # Check if it's an instruction
            h2 = root.xpath("h2[@class='instruction-section']")
            if len(h2) != 1:
                return None
            # Get instruction title and check it (it must NOT be "Shared Pseudocode Functions")
            title = h2[0].text
            if title == "Shared Pseudocode Functions":
                return None
            # Get an unique instr. ID
            instr_id = file_name.replace(".html", "")
            # Get instruction description
            description = XHTMLParser.get_instruction_description(root)
            # Get the instruction aliases
            aliases = self.get_aliases(root, file_name)
            # Is the instruction an alias?
            alias_p = root.xpath("p[text()[contains(.,'This is an alias of')]]")
            if len(alias_p) > 0:
                alias_id = alias_p[0].xpath("a")[0].get("href").replace(".html", "")
            else:
                alias_id = None
            # Do we have a classes for the instruction?
            class_headings = root.xpath("h3[@class='classheading']")
            if len(class_headings) > 0:
                # Yes, we do!
                instr = {
                    "type": "instruction",
                    "title": title,
                    "file": file_name,
                    "id": instr_id,
                    "description": description,
                    "has_aliases": aliases,
                    "alias_of": alias_id,
                    "classes": []
                }
                # Loop the classes
                for ch in class_headings:
                    # Find class title and architecture
                    class_title = ch.xpath("a")[0].text
                    arch = XHTMLParser.get_arch(ch)
                    # Find the regdiagram
                    regdiagram = ch.xpath("./following::div[@class='regdiagram-32']")
                    if len(regdiagram) == 0:
                        print "Error! %s must have a regdiagram for '%s' class heading!" % (
                            file_name, ch.text_content().strip()
                        )
                        exit()
                    # Get fields, masks and encodings for the instruction
                    fields = XHTMLParser.get_fields(regdiagram[0], file_name)
                    eq_mask, uneq_masks = XHTMLParser.get_masks(regdiagram[0])
                    encodings = XHTMLParser.get_encodings(regdiagram[0])
                    # Add the result to the result list
                    class_id = re.sub(r'[^[a-z0-9]', '_', class_title.lower())
                    class_id = instr_id + "_" + re.sub(r'_$', '', class_id) + "_cls"
                    instr["classes"].append(
                        {
                            "title": class_title,
                            "fields": fields,
                            "arch": arch,
                            "mask": eq_mask,
                            "unallocated": uneq_masks,
                            "encodings": encodings,
                            "id": class_id
                        }
                    )
                return instr
            else:
                # No, we don't -- parse the only regdiagram
                regdiagram = root.xpath("div[@class='regdiagram-32']")
                if len(regdiagram) != 1:
                    print "Error! %s must have exactly one regdiagram!" % file_name
                    exit()
                # Get fields, masks and encodings for the instruction
                fields = XHTMLParser.get_fields(regdiagram[0], file_name)
                eq_mask, uneq_masks = XHTMLParser.get_masks(regdiagram[0])
                encodings = XHTMLParser.get_encodings(regdiagram[0])
                # The result
                instr = {
                    "id": instr_id,
                    "type": "instruction",
                    "title": title,
                    "file": file_name,
                    "description": description,
                    "has_aliases": aliases,
                    "alias_of": alias_id,
                    "classes": [
                        {
                            "title": title,
                            "fields": fields,
                            "mask": eq_mask,
                            "unallocated": uneq_masks,
                            "encodings": encodings,
                            "id": instr_id + "_cls"
                        }
                    ]
                }
                return instr
        else:
            return None


if __name__ == "__main__":

    # Help text
    help = "The script converts an html ARM64 instruction encoding guide to a machine-readable JSON.\n" \
           "Usage:\n" \
           "\t$ python html2json.py <path/to/the/xhtml/folder> <path/to/the/output/json/file>\n" \
           "Please, use paths without spaces."

    # Check args
    if len(sys.argv) != 3 or sys.argv[1].lower() in ["--h", "-h", "--help", "-help", "-?"]:
        print help
        exit()

    # Do the job
    XHTMLParser(sys.argv[1], sys.argv[2])
