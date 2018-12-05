import xml.etree.ElementTree as ETree

def get_var_table(filename):
    var_table = {}
    translation_table = {}

    base = ETree.parse(filename).getroot()
    mvars = base.find('ModelVariables')

    for var in mvars.findall('ScalarVariable'):
        causality = var.get('causality')

        # In FMI 1.0, parameters have causality 'internal'
        if causality == 'internal': causality = 'parameter'

        name = var.get('name')
        if causality in ['input', 'output', 'parameter']:
            var_table.setdefault(causality, {})
            translation_table.setdefault(causality, {})
            # Variable names including '.' cannot be used in Python scripts - they get aliases with '_':
            if '.' in name:
                alt_name = name.replace('.', '_')
            else:
                alt_name = name
            translation_table[causality][alt_name] = name

            # Store variable type information:
            specs = var.getchildren()
            for spec in specs:
                if spec.tag in ['Real', 'Integer', 'Boolean', 'String']:
                    var_table[causality][name] = spec.tag
                    continue

    return var_table, translation_table