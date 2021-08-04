""" Defines a Flow Filtering syntax
"""
import pyparsing as pp
import netaddr

from ovs_dbg.decoders import decode_default, decode_int, Decoder, IPMask, EthMask

from ovs_dbg.fields import field_decoders


class ClauseExpression:
    operators = {}
    type_decoders = {
        int: decode_int,
        netaddr.IPAddress: IPMask,
        netaddr.EUI: EthMask,
        bool: bool,
    }

    def __init__(self, tokens):
        self.field = tokens[0]
        self.value = ""
        self.operator = ""

        if len(tokens) > 1:
            self.operator = tokens[1]
            self.value = tokens[2]

    def __repr__(self):
        return "{}(field: {}, operator: {}, value: {})".format(
            self.__class__.__name__, self.field, self.operator, self.value
        )

    def _find_data_in_kv(self, kv_list):
        """Find a value for evaluation in a list of KeyValue

        Args:
            kv_list (list[KeyValue]): list of KeyValue to look into
        """
        key_parts = self.field.split(".")
        field = key_parts[0]
        kvs = [kv for kv in kv_list if kv.key == field]
        if not kvs:
            return None

        for kv in kvs:
            if kv.key == self.field:
                # exact match
                return kv.value
            elif len(key_parts) > 1:
                data = kv.value
                for subkey in key_parts[1:]:
                    try:
                        data = data.get(subkey)
                    except Exception:
                        data = None
                        break
                    if not data:
                        break
                if data:
                    return data

    def _find_data(self, flow):
        """Finds the key-value to use for evaluation"""
        for section in flow.sections:
            data = self._find_data_in_kv(section.data)
            if data:
                return data
        return None

    def evaluate(self, flow):
        data = self._find_data(flow)
        if not data:
            return False

        if not self.value and not self.operator:
            # just asserting the existance of the key
            return True

        # Decode the value based on the type of data
        if isinstance(data, Decoder):
            decoder = data.__class__
        else:
            decoder = self.type_decoders.get(data.__class__) or decode_default

        decoded_value = decoder(self.value)

        if self.operator == "=":
            return decoded_value == data
        elif self.operator == "<":
            return data < decoded_value
        elif self.operator == ">":
            return data > decoded_value
        elif self.operator == "~=":
            return decoded_value in data


class BoolNot:
    def __init__(self, t):
        self.op, self.args = t[0]

    def __repr__(self):
        return "NOT({})".format(self.args)

    def evaluate(self, flow):
        return not self.args.evaluate(flow)


class BoolAnd:
    def __init__(self, pattern):
        self.args = pattern[0][0::2]

    def __repr__(self):
        return "AND({})".format(self.args)

    def evaluate(self, flow):
        return all([arg.evaluate(flow) for arg in self.args])


class BoolOr:
    def __init__(self, pattern):
        self.args = pattern[0][0::2]

    def evaluate(self, flow):
        return any([arg.evaluate(flow) for arg in self.args])

    def __repr__(self):
        return "OR({})".format(self.args)


class OFFilter:
    w = pp.Word(pp.alphanums + "." + ":" + "_" + "/" + "-")
    operators = (
        pp.Literal("=")
        | pp.Literal("~=")
        | pp.Literal("<")
        | pp.Literal(">")
        | pp.Literal("!=")
    )

    clause = (w + operators + w) | w
    clause.setParseAction(ClauseExpression)

    statement = pp.infixNotation(
        clause,
        [
            ("!", 1, pp.opAssoc.RIGHT, BoolNot),
            ("not", 1, pp.opAssoc.RIGHT, BoolNot),
            ("&&", 2, pp.opAssoc.LEFT, BoolAnd),
            ("and", 2, pp.opAssoc.LEFT, BoolAnd),
            ("||", 2, pp.opAssoc.LEFT, BoolOr),
            ("or", 2, pp.opAssoc.LEFT, BoolOr),
        ],
    )

    def __init__(self, expr):
        self._filter = self.statement.parseString(expr)

    def evaluate(self, flow):
        return self._filter[0].evaluate(flow)
