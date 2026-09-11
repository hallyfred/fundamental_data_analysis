{% macro prepare_ci_schema() %}
    {# Unit tests use temporary relations in the target dataset. #}
    {% if target.name != 'ci' %}
        {{ exceptions.raise_compiler_error('prepare_ci_schema requires --target ci') }}
    {% endif %}
    {% if execute %}
        {% do adapter.create_schema(api.Relation.create(database=target.database, schema=target.schema)) %}
    {% endif %}
{% endmacro %}
