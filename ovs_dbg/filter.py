""" Defines a Flow Filtering syntax
"""
import pyparsing as pp
import netaddr

from ovs_dbg.decoders import decode_default
from ovs_dbg.fields import field_decoders


class ClauseExpression:
    operators = {}
    decoders = {
        "nw_src": netaddr.IPNetwork,
        **field_decoders,
    }

    def __init__(self, tokens):
        self.field = tokens[0]
        if len(tokens) <= 1:
            self.operator = "="
            self.value_raw = True
            self.value = True
        else:
            self.operator = tokens[1]
            self.value_raw = tokens[2]
            self.value = (
                self.decoders.get(self.field)(self.value_raw)
                if self.decoders.get(self.field)
                else decode_default(self.value_raw)
            )
            if isinstance(self.value, str) and self.value == "true":
                self.value = True
            elif isinstance(self.value, str) and self.value == "false":
                self.value = False

    def __repr__(self):
        return "{}(field: {}, operator: {}, value: {})".format(
            self.__class__.__name__, self.field, self.operator, self.value_raw
        )

    def evaluate(self, flow):
        data = flow.info.get(self.field) or flow.match.get(self.field)

        if not data:
            # search in actions
            act_parts = self.field.split(".")
            act_name = act_parts[0]
            actions = [act for act in flow.actions_kv if act.key == act_name]
            if not actions:
                return False

            # Look into arguments
            for action in actions:
                if action.key == self.field:
                    # exact match
                    data = action.value
                    break
                elif len(act_parts) > 1:
                    data = action.value
                    for key in act_parts[1:]:
                        data = data.get(key)
                        if not data:
                            break
            if not data:
                return False

        if self.operator == "=":
            return self.value == data
        elif self.operator == "<":
            return data < self.value
        elif self.operator == ">":
            return data > self.value
        elif self.operator == "~=":
            return self.value in data


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
        # print(pattern)

    def __repr__(self):
        return "AND({})".format(self.args)

    def evaluate(self, flow):
        return all([arg.evaluate(flow) for arg in self.args])


class BoolOr:
    def __init__(self, pattern):
        self.args = pattern[0][0::2]
        # print(pattern)

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
        print(self._filter)

    def evaluate(self, flow):
        return self._filter[0].evaluate(flow)
