##########################################################################
#######################
from __future__ import print_function, unicode_literals

from django.contrib.admin import helpers
from django.contrib.admin.options import get_content_type_for_model
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_text
from django.utils.translation import ugettext as _

#######################

##########################################################################


class AdminSiteViewMixin(object):
    """
    Use this for generic CBVs in the admin.
    Still need to check permissions and hook into admin urls appropriately.
    """

    def get_admin_options(self):
        return self.kwargs.get("admin_options", None)

    def get_context_data(self, **kwargs):
        """
        Extend the context so the admin template works properly.
        """
        context = super(AdminSiteViewMixin, self).get_context_data(**kwargs)
        admin_options = self.get_admin_options()
        context.update(
            admin_options.admin_site.each_context(self.request),
            model=admin_options.model,
            opts=admin_options.model._meta,
            app_label=admin_options.model._meta.app_label,
        )
        return context


################################################################


class AdminFormMixin(object):

    model = None
    _obj_cache = None

    def get_original_obj(self):
        if self._obj_cache is not None:
            return self._obj_cache
        pk = self.kwargs.get("pk", None)
        if self.model is None:
            raise ImplementationError("AdminFormMixin requires the model attribute.")
        obj = get_object_or_404(self.model, pk=pk)
        self._obj_cache = obj
        return obj

    def get_success_url(self):
        """
        Note that this requires the underlying model to define the
        ``admin_change_link()`` method::

    def admin_change_link(self):
        return reverse('admin:{}_{}_change'.format(self._meta.app_label,
                            self._meta.model_name), args=[self.pk, ])

        """
        obj = self.get_original_obj()
        return obj.admin_change_link()

    def get_context_data(self, **kwargs):
        """
        Extend the context so the admin template works properly.
        """
        context = super(AdminFormMixin, self).get_context_data(**kwargs)
        context.update(original=self.get_original_obj())
        return context


################################################################


class ClassBasedViewsAdminMixin(object):
    """
    Utility functions for making use of CBVs in Django admin.

    This still needs work for greater utility.

    E.g., this does *not* check any permissions: wrap with
    ``from django.contrib.auth.decorators import permission_required``
    if needed.


    You'll still need to add urls using get_urls()::

    def get_urls(self):
        urls = super(..., self).get_urls()
        urls = [url(r'^extra-action/$',
                    self.admin_site.admin_view(self.cb_changeform_view),
                    kwargs={'view_class': ViewClass, }
                    name='...',
                    ),
                ] + urls
        return  urls
    """

    def cb_changeform_view(self, request, *args, **kwargs):
        """
        Like a change view in the admin.
        """
        view_class = kwargs.get("view_class")
        add = kwargs.get("add", True)
        obj = kwargs.get("original", None)
        object_id = kwargs.get("object_id", None)
        title = kwargs.get("title", None)

        if hasattr(view_class, "form_class"):
            form = view_class.form_class()
        else:
            form = None
        formsets = []
        opts = self.model._meta
        TO_FIELD_VAR = False
        IS_POPUP_VAR = False
        change = not True
        view_on_site_url = None
        form_url = ""
        app_label = opts.app_label
        if form is not None:
            adminForm = helpers.AdminForm(form, formsets, {}, None, model_admin=self)
            media = self.media + adminForm.media
            admin_error_list = helpers.AdminErrorList(form, formsets)
        else:
            adminForm = None
            media = self.media
            admin_error_list = None
        to_field = request.POST.get(TO_FIELD_VAR, request.GET.get(TO_FIELD_VAR))
        inline_formsets = None

        # From ``changeform_view``
        if title is None:
            title = (_("Bulk add %s") if add else _("Bulk change %s")) % force_text(
                opts.verbose_name_plural
            )
        context = dict(
            self.admin_site.each_context(request),
            title=title,
            adminform=adminForm,
            object_id=object_id,
            original=obj,
            is_popup=(IS_POPUP_VAR in request.POST or IS_POPUP_VAR in request.GET),
            to_field=to_field,
            media=media,
            inline_admin_formsets=inline_formsets,
            errors=admin_error_list,
            preserved_filters=self.get_preserved_filters(request),
        )
        # From ``render_change_form``
        context.update(
            {
                "add": add,
                "change": change,
                "has_add_permission": self.has_add_permission(request),
                "has_change_permission": self.has_change_permission(request, obj),
                "has_delete_permission": self.has_delete_permission(request, obj),
                "has_file_field": True,  # FIXME - this should check if form or formsets have a FileField,
                "has_absolute_url": view_on_site_url is not None,
                "absolute_url": view_on_site_url,
                "form_url": form_url,
                "opts": opts,
                "content_type_id": get_content_type_for_model(self.model).pk,
                "save_as": self.save_as,
                "save_on_top": self.save_on_top,
                "to_field_var": TO_FIELD_VAR,
                "is_popup_var": IS_POPUP_VAR,
                "app_label": app_label,
                "media": self.media,
            }
        )

        original_get_context_data = view_class.get_context_data

        def _monkey_patch_get_context_data(instance, *args, **kwargs):
            data = original_get_context_data(instance, *args, **kwargs)
            data.update(context)
            return data

        view_class.get_context_data = _monkey_patch_get_context_data
        return view_class.as_view()(request)


##########################################################################
