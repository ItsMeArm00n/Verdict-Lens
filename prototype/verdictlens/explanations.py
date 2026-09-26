"""Local template explanation; no LLM or network dependency."""
def explain(result):
    p = result['primary']
    text = f"The demo primary model returns {p['decision']} with estimated risk {p['risk_estimate']:.1%}, using a {p['threshold']:.1%} threshold. "
    if result['flags']:
        text += 'Review signals: ' + ', '.join(result['flags']) + '. These signals do not establish that the decision is incorrect.'
    else:
        text += 'No flags were found in the configured checks; this is not a guarantee of correctness.'
    return text
