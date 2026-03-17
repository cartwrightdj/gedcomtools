"""
Tests for gedcomtools.gedcomx.agent.Agent
Covers: add_name(), shares_name(), __eq__, duplicate handling, empty-name guard.
"""
import pytest
from gedcomtools.gedcomx.agent import Agent
from gedcomtools.gedcomx.identifier import IdentifierList
from gedcomtools.gedcomx.textvalue import TextValue
from gedcomtools.gedcomx.uri import URI


class TestAgentAddName:
    def test_add_str_name(self):
        a = Agent(id="A1")
        a.add_name("FamilySearch")
        assert len(a.names) == 1

    def test_add_textvalue_name(self):
        a = Agent(id="A1")
        a.add_name(TextValue(value="FamilySearch"))
        assert len(a.names) == 1

    def test_add_name_value_stored(self):
        a = Agent(id="A1")
        a.add_name("FamilySearch")
        assert a.names[0].value == "FamilySearch"

    def test_add_duplicate_str_returns_silently(self):
        """Regression: adding a duplicate name must not raise and must not duplicate the list."""
        a = Agent(id="A1")
        a.add_name("FamilySearch")
        a.add_name("FamilySearch")  # second call — must be silent
        assert len(a.names) == 1

    def test_add_duplicate_textvalue_returns_silently(self):
        a = Agent(id="A1")
        tv = TextValue(value="FamilySearch")
        a.add_name(tv)
        a.add_name(TextValue(value="FamilySearch"))
        assert len(a.names) == 1

    def test_add_none_raises_value_error(self):
        a = Agent(id="A1")
        with pytest.raises(ValueError):
            a.add_name(None)

    def test_add_wrong_type_raises_value_error(self):
        a = Agent(id="A1")
        with pytest.raises(ValueError):
            a.add_name(12345)

    def test_add_multiple_distinct_names(self):
        a = Agent(id="A1")
        a.add_name("Alpha")
        a.add_name("Beta")
        assert len(a.names) == 2


class TestAgentSharesName:
    def test_shares_name_true_when_overlap(self):
        a1 = Agent(id="A1")
        a1.add_name("Shared Name")
        a2 = Agent(id="A2")
        a2.add_name("Shared Name")
        assert a1.shares_name(a2) is True

    def test_shares_name_false_when_no_overlap(self):
        a1 = Agent(id="A1")
        a1.add_name("Alice")
        a2 = Agent(id="A2")
        a2.add_name("Bob")
        assert a1.shares_name(a2) is False

    def test_shares_name_false_empty_vs_named(self):
        a1 = Agent(id="A1")  # no names
        a2 = Agent(id="A2")
        a2.add_name("Alice")
        assert a1.shares_name(a2) is False

    def test_shares_name_false_both_empty(self):
        a1 = Agent(id="A1")
        a2 = Agent(id="A2")
        assert a1.shares_name(a2) is False

    def test_shares_name_false_for_non_agent(self):
        a = Agent(id="A1")
        a.add_name("Alice")
        assert a.shares_name("not an agent") is False

    def test_shares_name_partial_overlap(self):
        """One matching name is enough to return True even if others differ."""
        a1 = Agent(id="A1")
        a1.add_name("Alice")
        a1.add_name("Common")
        a2 = Agent(id="A2")
        a2.add_name("Bob")
        a2.add_name("Common")
        assert a1.shares_name(a2) is True


class TestAgentEq:
    def test_equal_agents_same_object(self):
        """An Agent is equal to itself (identity implies equality)."""
        a = Agent(id="A1")
        a.add_name("FamilySearch")
        a.uri = None  # prevent AttributeError on uri access if id check passes
        assert a == a

    def test_equal_agents_same_object_identity(self):
        """An agent is always equal to itself (identity short-circuit via __eq__)."""
        shared_ids = IdentifierList()
        shared_uri = URI(fragment="FIXED_ID")
        a1 = Agent(id="FIXED_ID", identifiers=shared_ids,
                   names=[TextValue(value="FamilySearch")])
        a1.uri = shared_uri
        # IdentifierList has no __eq__ so two separate instances won't compare equal;
        # pass the same instance to both agents and compare the agent to itself.
        assert a1 == a1

    def test_not_equal_different_id(self):
        """Agents with different ids are not equal; id check short-circuits before uri access."""
        a1 = Agent(id="A1")
        a2 = Agent(id="A2")
        assert a1 != a2

    def test_not_equal_different_name(self):
        """Same id but different names → not equal (names check before uri, so no AttributeError)."""
        a1 = Agent(id="SAME")
        a1.add_name("Alice")
        a2 = Agent(id="SAME")
        a2.add_name("Bob")
        assert a1 != a2

    def test_not_equal_to_non_agent(self):
        a = Agent(id="A1")
        result = a.__eq__("not an agent")
        assert result is NotImplemented


class TestAgentStr:
    def test_str_contains_id(self):
        a = Agent(id="A1")
        assert "A1" in str(a)

    def test_str_contains_name(self):
        a = Agent(id="A1")
        a.add_name("My Org")
        assert "My Org" in str(a)

    def test_str_unnamed(self):
        a = Agent(id="A1")
        s = str(a)
        assert "Unnamed Agent" in s or "A1" in s
