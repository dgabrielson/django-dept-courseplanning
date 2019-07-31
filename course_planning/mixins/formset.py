class UpdateViewWithFormset(object):
    """
    Like a regular update view, except there's also exactly one
    formset associated as well.  Both ``form`` and ``formset``
    are passed as context variables.
    """

    formset_class = None
    formset_initial = None
    formset_prefix = None

    def get_formset_class(self):
        if self.formset_class is None:
            raise ImplementationError(
                "You must either supply a formset_class attribte or override the get_formset_class method"
            )
        return self.formset_class

    def get_formset_initial(self):
        """
        Returns the initial data to use for forms on this view.
        """
        if self.formset_initial is None:
            self.formset_initial = {}
        return self.formset_initial.copy()

    def get_formset_prefix(self):
        """
        Returns the prefix to use for forms on this view
        """
        return self.formset_prefix

    def get_formset_kwargs(self):
        kwargs = {
            "initial": self.get_formset_initial(),
            "prefix": self.get_formset_prefix(),
            "instance": self.object,
        }

        if self.request.method in ("POST", "PUT"):
            kwargs.update({"data": self.request.POST, "files": self.request.FILES})
        return kwargs

    def get_formset(self, formset_class=None):
        """
        Returns an instance of the form to be used in this view.
        """
        if formset_class is None:
            formset_class = self.get_formset_class()
        return formset_class(**self.get_formset_kwargs())

    def get_context_data(self, **kwargs):
        """
        Insert the form into the context dict.
        """
        context = super().get_context_data(**kwargs)
        if "formset" not in context:
            context["formset"] = self.get_formset()
        return context

    def form_valid(self, form, formset):
        """
        If the form is valid, save the associated model.
        """
        result = super().form_valid(form)
        formset.save()
        return result

    def form_invalid(self, form, formset):
        """
        If the form is invalid, re-render the context data with the
        data-filled form and errors.
        """
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset)
        )

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        self.object = self.get_object()
        form = self.get_form()
        formset = self.get_formset()
        if form.is_valid() and formset.is_valid():
            return self.form_valid(form, formset)
        else:
            return self.form_invalid(form, formset)
