%global builddate $(date +"%%Y%%m%%d-%%T")
%global commit_version "d48f381d9a4e68c83283ce5233844807dfdc5ba5"

Name:           prometheus
Version:        2.36.0
Release:        2%{?dist}
Summary:        Prometheus monitoring system and time series database
Vendor:         Microsoft Corporation
Distribution:   Mariner
License:        ASL 2.0
URL:            https://github.com/prometheus/prometheus
Source0:        https://github.com/prometheus/prometheus/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz
# unzip Source0
# run 'make build' in it
# tar       --sort=name \
#           --mtime="2021-04-26 00:00Z" \
#           --owner=0 --group=0 --numeric-owner \
#           --pax-option=exthdr.name=%d/PaxHeaders/%f,delete=atime,delete=ctime \
#           -cf web-ui-%%{version}.tar.gz web/ui
Source10:       web-ui-%{version}.tar.gz
Source1:        prometheus.service
Source2:        prometheus.sysconfig
Source3:        prometheus.yml
Source4:        prometheus.conf
Source5:        prometheus.logrotate
# On version updates run "toolkit/scripts/build_go_vendor_cache.sh %%{name}-%%{version}.tar.gz"
Source6:        %{name}-%{version}-vendor.tar.gz

# Debian patch for default settings
Patch0:         02-Default_settings.patch

BuildRequires:  systemd-rpm-macros
BuildRequires:  golang
Requires(pre):  /usr/bin/systemd-sysusers

%description
The Prometheus monitoring system and time series database

%prep
%autosetup -p1

%build
rm -rf web/ui
tar -xf %{SOURCE10}

rm -rf vendor
tar -xf %{SOURCE6} --no-same-owner

export LDFLAGS="-X github.com/prometheus/common/version.Version=%{version} \
                -X github.com/prometheus/common/version.Revision=%{commit_version} \
                -X github.com/prometheus/common/version.Branch=master \
                -X github.com/prometheus/common/version.BuildUser=mockbuild \
                -X github.com/prometheus/common/version.BuildDate=%{builddate} "
export BUILDTAGS="netgo builtinassets"
for cmd in cmd/* ; do
  go build -ldflags "$LDFLAGS" -mod=vendor -v -a -tags "$BUILDTAGS" -o $(basename $cmd) ./$cmd
done

%install
install -m 0755 -vd                     %{buildroot}%{_bindir}
install -m 0755 -vp prometheus          %{buildroot}%{_bindir}/
install -m 0755 -vp promtool            %{buildroot}%{_bindir}/

# Unit file
install -m 0755 -vd                     %{buildroot}%{_unitdir}
install -m 0644 -vp %{SOURCE1}          %{buildroot}%{_unitdir}/

install -m 0755 -vd                     %{buildroot}%{_sysconfdir}
install -m 0755 -vd                     %{buildroot}%{_sysconfdir}/prometheus
install -m 0644 -vp %{SOURCE3}          %{buildroot}%{_sysconfdir}/prometheus/
install -m 0755 -vd                     %{buildroot}%{_sysconfdir}/sysconfig
install -m 0644 -vp %{SOURCE2}          %{buildroot}%{_sysconfdir}/sysconfig/prometheus
install -m 0755 -vd                     %{buildroot}%{_sysconfdir}/logrotate.d
install -m 0644 -vp %{SOURCE5}          %{buildroot}%{_sysconfdir}/logrotate.d/prometheus
install -m 0755 -vd                     %{buildroot}%{_sysusersdir}
install -m 0644 -vp %{SOURCE4}          %{buildroot}%{_sysusersdir}/

mkdir -p %{buildroot}%{_sysconfdir}/prometheus/consoles
mkdir -p %{buildroot}%{_sysconfdir}/prometheus/console_libraries
mkdir -p %{buildroot}%{_sharedstatedir}/prometheus

%pre
%sysusers_create_package prometheus %{SOURCE4}

%post
%systemd_post prometheus.service

%preun
%systemd_preun prometheus.service

%postun
%systemd_postun_with_restart prometheus.service

%check
# scrape: needs network
# tsdb: https://github.com/prometheus/prometheus/issues/8393
# NOTE '%gocheck' is avalible via go-rpm-tools which is currently in SPECS-EXTENDED
# use the raw go test till we import go-rpm-macros to CBL-Mariner core
# go check -t cmd -d scrape -d discovery/kubernetes -d web -d tsdb -d tsdb/chunks
go_test_status=0
go test -v ./scrape/
check_result=$?
if [[ $check_result -ne 0 ]]; then
    go_test_status=1
fi
go test -v ./discovery/...
check_result=$?
if [[ $check_result -ne 0 ]]; then
    go_test_status=1
fi
go test -v ./web/
check_result=$?
if [[ $check_result -ne 0 ]]; then
    go_test_status=1
fi
go test -v ./tsdb/...
check_result=$?
if [[ $check_result -ne 0 ]]; then
    go_test_status=1
fi
go test -v ./cmd/prometheus/
check_result=$?
if [[ $check_result -ne 0 ]]; then
    go_test_status=1
fi

[[ go_test_status -eq 0 ]]

%files
%license LICENSE NOTICE
%doc docs CHANGELOG.md MAINTAINERS.md CODE_OF_CONDUCT.md CONTRIBUTING.md
%doc README.md RELEASE.md documentation
%dir %{_sysconfdir}/prometheus/
%dir %{_sysconfdir}/prometheus/consoles
%dir %{_sysconfdir}/prometheus/console_libraries
%config(noreplace) %{_sysconfdir}/sysconfig/prometheus
%config(noreplace) %{_sysconfdir}/prometheus/prometheus.yml
%config(noreplace) %{_sysconfdir}/logrotate.d/prometheus
%{_bindir}/*
%{_unitdir}/prometheus.service
%{_sysusersdir}/prometheus.conf
%attr(0755,prometheus,prometheus) %{_sharedstatedir}/prometheus

%changelog
* Tue Jun 14 2022 Muhammad Falak <mwani@microsoft.com> - 2.36.0-2
- Bump release to rebuild with golang 1.18.3

* Mon Jun 06 2022 Pawel Winogrodzki <pawelwi@microsoft.com> - 2.36.0-1
- Updating to version 2.36.0 to fix CVE-2021-29622.

* Mon Jan 31 2022 Muhammad Falak <mwani@microsoft.com> - 2.24.1-8
- Fix ptest by using 'go test' instead of 'go check'
- Backport a patch to fix test in 'tsdb/chunks'

* Wed Jul 28 2021 Henry Li <lihl@microsoft.com> - 2.24.1-7
- Initial CBL-Mariner import from Fedora 34 (license: MIT)
- License Verified
- Use golang for BR
- Use prebuilt go vendor tarball for building
- Remove unused/un-supported macro usage

* Tue Jun 15 17:51:49 CEST 2021 Robert-André Mauchin <zebob.m@gmail.com> - 2.24.1-6
- Add systemd-sysusers as Requires
- Fix: rhbz#1972026

* Sun Mar 28 18:57:11 CEST 2021 Robert-André Mauchin <zebob.m@gmail.com> - 2.24.1-5
- Add ExecReload to service file

* Tue Mar 02 2021 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl> - 2.24.1-4
- Rebuilt for updated systemd-rpm-macros
  See https://pagure.io/fesco/issue/2583.

* Tue Jan 26 22:05:24 CET 2021 Robert-André Mauchin <zebob.m@gmail.com> - 2.24.1-3
- Set default settings in main.go
- Embedded assets in the binary
- Added a logrotate file
- Fix: rhbz#1902496

* Tue Jan 26 2021 Fedora Release Engineering <releng@fedoraproject.org> - 2.24.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_34_Mass_Rebuild

* Thu Jan 21 19:43:35 CET 2021 Robert-André Mauchin <zebob.m@gmail.com> - 2.24.1-1
- Update to 2.24.1
- Close: rhbz#1918532

* Thu Jan  7 17:40:17 CET 2021 Robert-André Mauchin <zebob.m@gmail.com> - 2.24.0-1
- Update to 2.24.0
- Close: rhbz#1911731

* Sat Dec 05 22:54:14 CET 2020 Robert-André Mauchin <zebob.m@gmail.com> - 2.23.0-2
- Add new React based UI
- Fix rhbz#1902496

* Thu Dec 03 13:12:59 CET 2020 Robert-André Mauchin <zebob.m@gmail.com> - 2.23.0-1
- Update to 2.23.0
- Add configuration
- Close rhbz#1866613
- Fix rhbz#1894089
- Fix rhbz#1902496

* Sat Aug 01 2020 Fedora Release Engineering <releng@fedoraproject.org> - 2.20.0-2
- Second attempt - Rebuilt for
  https://fedoraproject.org/wiki/Fedora_33_Mass_Rebuild

* Thu Jul 30 22:32:01 CEST 2020 Robert-André Mauchin <zebob.m@gmail.com> - 2.20.0-1
- Update to 2.20.0

* Mon Jul 27 2020 Fedora Release Engineering <releng@fedoraproject.org> - 2.11.0-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_33_Mass_Rebuild

* Mon Feb 17 2020 Elliott Sales de Andrade <quantum.analyst@gmail.com> - 2.11.0-4
- Rebuilt for GHSA-jf24-p9p9-4rjh

* Wed Jan 29 2020 Fedora Release Engineering <releng@fedoraproject.org> - 2.11.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_32_Mass_Rebuild

* Thu Jul 25 2019 Fedora Release Engineering <releng@fedoraproject.org> - 2.11.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_31_Mass_Rebuild

* Tue Jul 09 19:29:38 CEST 2019 Robert-André Mauchin <zebob.m@gmail.com> - 2.11.0-1
- Release 2.11.0

* Tue Jul 09 2019 Elliott Sales de Andrade <quantum.analyst@gmail.com> - 2.9.2-2
- Add Obsoletes for old names

* Wed May 15 03:08:50 CEST 2019 Robert-André Mauchin <zebob.m@gmail.com> - 2.9.2-1
- Release 2.9.2

* Fri Feb 01 2019 Fedora Release Engineering <releng@fedoraproject.org> - 1.8.0-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_30_Mass_Rebuild

* Fri Jul 13 2018 Fedora Release Engineering <releng@fedoraproject.org> - 1.8.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_29_Mass_Rebuild

* Wed Feb 07 2018 Fedora Release Engineering <releng@fedoraproject.org> - 1.8.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Tue Oct 10 2017 Jan Chaloupka <jchaloup@redhat.com> - 1.8.0-1
- Update to 1.8.0
  resolves: #1495180

* Tue Aug 22 2017 Jan Chaloupka <jchaloup@redhat.com> - 0.15.0-8
- Polish the spec file

* Wed Aug 02 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.15.0-7
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.15.0-6
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Fri Feb 10 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.15.0-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Thu Jul 21 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.15.0-4
- https://fedoraproject.org/wiki/Changes/golang1.7

* Mon Feb 22 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.15.0-3
- https://fedoraproject.org/wiki/Changes/golang1.6

* Wed Feb 03 2016 Fedora Release Engineering <releng@fedoraproject.org> - 0.15.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Thu Jul 23 2015 jchaloup <jchaloup@redhat.com> - 0.15.0-1
- Update to 0.15.0
  resolves: #1246058

* Wed Jun 17 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 0.13.3-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Wed May 13 2015 jchaloup <jchaloup@redhat.com> - 0.13.3-2
- Add debug info
  related: #1190426

* Tue May 12 2015 jchaloup <jchaloup@redhat.com> - 0.13.3-1
- Update to 0.13.3
  related: #1190426

* Sat May 09 2015 jchaloup <jchaloup@redhat.com> - 0.13.2-1
- Update to 0.13.2
  related: #1190426

* Sat Feb 07 2015 jchaloup <jchaloup@redhat.com> - 0-0.1.git4e6a807
- First package for Fedora
  resolves: #1190426
