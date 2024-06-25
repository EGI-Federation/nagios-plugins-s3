# Package needs to stay arch specific (due to nagios plugins location), but
# there's nothing to extract debuginfo from
%global debug_package %{nil}

%define nagios_plugins_dir %{_libdir}/nagios/plugins

Name:       nagios-plugins-s3
Version:    0.0.1
Release:    1%{?dist}
Summary:    Nagios probes to be run remotely against s3 endpoints
License:    MIT
Group:      Applications/Internet
URL:        https://github.com/EGI-Federation/nagios-plugins-storage
# The source of this package was pulled from upstream's vcs. Use the
# following commands to generate the tarball:
Source0:   %{name}-%{version}.tar.gz
Buildroot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch: noarch

Requires:   nagios%{?_isa}
Requires:   python3
Requires:   python3-nap
Requires:   python3-botocore
Requires:   python3-boto3

%description
This package provides the nagios probes for s3

%prep
%setup -q -n %{name}-%{version}

%build

%install
make install DESTDIR=%{buildroot}
mkdir -p %{buildroot}%{_libdir}/nagios/plugins/s3
cp --preserve=timestamps plugins/*.py %{buildroot}%{_libdir}/nagios/plugins/s3

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{nagios_plugins_dir}/s3
%doc LICENSE README.md

%changelog
* Wed Jun 26 2024 Andrea Manzi <andrea.manzi@egi.eu> - 0.0.1-0
- first version
