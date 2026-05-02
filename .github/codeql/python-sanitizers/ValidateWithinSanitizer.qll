/**
 * Custom sanitizer for Evidentia's `evidentia_core.security.paths.validate_within`
 * helper. The function resolves a candidate path and asserts it sits inside a
 * permitted directory; if not, it raises `PathTraversalError`. Any flow
 * through this function emerges sanitized for path-injection purposes.
 *
 * Closes the false-positive HIGH alerts that the default `py/path-injection`
 * query produces against the helper itself + its downstream callsites:
 *  - #73 `evidentia_core/security/paths.py:91` (the resolve() call inside
 *    the validator; CodeQL doesn't recognize that the next two lines
 *    re-resolve and assert is_relative_to)
 *  - #72 `evidentia_core/gap_store.py:185` (read_text on a path returned
 *    by validate_within)
 *  - #71 `evidentia_core/gap_store.py:182` (is_file check on the same
 *    sanitized path)
 *
 * v0.7.7 CF3.
 */

import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.dataflow.new.TaintTracking
import semmle.python.security.dataflow.PathInjectionCustomizations
import semmle.python.ApiGraphs

/**
 * The data-flow node corresponding to a call to
 * `evidentia_core.security.paths.validate_within(...)`. Both the call
 * itself and its return value are treated as sanitized — taint flow
 * stops here.
 */
private DataFlow::Node validateWithinCall() {
  result = API::moduleImport("evidentia_core")
              .getMember("security")
              .getMember("paths")
              .getMember("validate_within")
              .getACall()
}

/**
 * Sanitizer for `py/path-injection`: the return value of `validate_within`
 * is a sanitized Path. Any read / write / open against that path
 * cannot be path-injection because the helper raises
 * `PathTraversalError` when the resolved candidate sits outside the
 * declared safe-root.
 */
class ValidateWithinSanitizer extends PathInjection::Sanitizer {
  ValidateWithinSanitizer() { this = validateWithinCall() }
}
