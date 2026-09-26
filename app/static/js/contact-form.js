document.addEventListener("DOMContentLoaded", function () {
  var form = document.querySelector(".contact-form");
  if (!form) return;

  var fields = form.querySelectorAll("input[required], textarea[required]");

  fields.forEach(function (field) {
    field.addEventListener("blur", function () {
      field.classList.toggle("field-invalid", !field.checkValidity());
    });
    field.addEventListener("input", function () {
      if (field.classList.contains("field-invalid")) {
        field.classList.toggle("field-invalid", !field.checkValidity());
      }
    });
  });

  form.addEventListener("submit", function () {
    if (!form.checkValidity()) return;

    var submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = "Sending…";
    }
  });
});
