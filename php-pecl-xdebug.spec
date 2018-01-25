# Fedora spec file for php-pecl-xdebug
#
# Copyright (c) 2010-2018 Remi Collet
# Copyright (c) 2006-2009 Christopher Stone
#
# License: MIT
# http://opensource.org/licenses/MIT
#
# Please, preserve the changelog entries
#

# we don't want -z defs linker flag
%undefine _strict_symbol_defs_build

%global pecl_name  xdebug
%global with_zts   0%{!?_without_zts:%{?__ztsphp:1}}
# XDebug should be loaded after opcache
%global ini_name   15-%{pecl_name}.ini
%global with_tests 0%{!?_without_tests:1}

%global gh_commit  e53e2073568dc26a74b73479bff4e3fd88fe3ab2
%global gh_short   %(c=%{gh_commit}; echo ${c:0:7})
#global gh_date    20171018
%global prever     RC2

Name:           php-pecl-xdebug
Summary:        PECL package for debugging PHP scripts
Version:        2.6.0
%if 0%{?prever:1}
Release:        0.5.%{prever}%{?dist}
%else
%if 0%{?gh_date:1}
Release:        0.2.%{gh_date}.%{gh_short}%{?dist}
%else
Release:        3%{?dist}
%endif
%endif
Source0:        https://github.com/%{pecl_name}/%{pecl_name}/archive/%{gh_commit}/%{pecl_name}-%{version}%{?prever}-%{gh_short}.tar.gz

# The Xdebug License, version 1.01
# (Based on "The PHP License", version 3.0)
License:        PHP
Group:          Development/Languages
URL:            http://xdebug.org/

BuildRequires:  php-pear  > 1.9.1
BuildRequires:  php-devel > 7
BuildRequires:  php-simplexml
BuildRequires:  libedit-devel
BuildRequires:  libtool

Requires:       php(zend-abi) = %{php_zend_api}
Requires:       php(api) = %{php_core_api}

Provides:       php-%{pecl_name} = %{version}
Provides:       php-%{pecl_name}%{?_isa} = %{version}
Provides:       php-pecl(Xdebug) = %{version}
Provides:       php-pecl(Xdebug)%{?_isa} = %{version}


%description
The Xdebug extension helps you debugging your script by providing a lot of
valuable debug information. The debug information that Xdebug can provide
includes the following:

* stack and function traces in error messages with:
  o full parameter display for user defined functions
  o function name, file name and line indications
  o support for member functions
* memory allocation
* protection for infinite recursions

Xdebug also provides:

* profiling information for PHP scripts
* code coverage analysis
* capabilities to debug your scripts interactively with a debug client


%prep
%setup -qc
mv %{pecl_name}-%{gh_commit} NTS

%if 0%{?gh_date:1}
%{__php} -r '
  $pkg = simplexml_load_file("NTS/package.xml");
  $pkg->date = substr("%{gh_date}",0,4)."-".substr("%{gh_date}",4,2)."-".substr("%{gh_date}",6,2);
  $pkg->version->release = "%{version}dev";
  $pkg->stability->release = "devel";
  $pkg->asXML("package.xml");
'
%else
mv NTS/package.xml .
%endif

sed -e '/LICENSE/s/role="doc"/role="src"/' -i package.xml

cd NTS
# Check extension version
ver=$(sed -n '/XDEBUG_VERSION/{s/.* "//;s/".*$//;p}' php_xdebug.h)
if test "$ver" != "%{version}%{?prever}%{?gh_date:-dev}"; then
   : Error: Upstream XDEBUG_VERSION version is ${ver}, expecting %{version}%{?prever}%{?gh_date:-dev}.
   exit 1
fi
cd ..

%if %{with_zts}
# Duplicate source tree for NTS / ZTS build
cp -pr NTS ZTS
%endif

cat << 'EOF' | tee %{ini_name}
; Enable xdebug extension module
zend_extension=%{pecl_name}.so

EOF
sed -e '1d' NTS/%{pecl_name}.ini >>%{ini_name}


%build
cd NTS
%{_bindir}/phpize
%configure \
    --enable-xdebug  \
    --with-php-config=%{_bindir}/php-config
make %{?_smp_mflags}

# Build debugclient
pushd debugclient
# buildconf required for aarch64 support
./buildconf
%configure --with-libedit
make %{?_smp_mflags}
popd

%if %{with_zts}
cd ../ZTS
%{_bindir}/zts-phpize
%configure \
    --enable-xdebug  \
    --with-php-config=%{_bindir}/zts-php-config
make %{?_smp_mflags}
%endif


%install
# install NTS extension
make -C NTS install INSTALL_ROOT=%{buildroot}

# install debugclient
install -Dpm 755 NTS/debugclient/debugclient \
        %{buildroot}%{_bindir}/debugclient

# install package registration file
install -Dpm 644 package.xml %{buildroot}%{pecl_xmldir}/%{name}.xml

# install config file
install -Dpm 644 %{ini_name} %{buildroot}%{php_inidir}/%{ini_name}

%if %{with_zts}
# Install ZTS extension
make -C ZTS install INSTALL_ROOT=%{buildroot}

install -Dpm 644 %{ini_name} %{buildroot}%{php_ztsinidir}/%{ini_name}
%endif

# Documentation
for i in $(grep 'role="doc"' package.xml | sed -e 's/^.*name="//;s/".*$//')
do
  [ -f NTS/contrib/$i ] && j=contrib/$i || j=$i
  install -Dpm 644 NTS/$j %{buildroot}%{pecl_docdir}/%{pecl_name}/$j
done


%check
# Shared needed extensions
modules=""
for mod in simplexml; do
  if [ -f %{php_extdir}/${mod}.so ]; then
    modules="$modules -d extension=${mod}.so"
  fi
done

# only check if build extension can be loaded
%{_bindir}/php \
    --no-php-ini \
    --define zend_extension=%{buildroot}%{php_extdir}/%{pecl_name}.so \
    --modules | grep Xdebug

%if %{with_zts}
%{_bindir}/zts-php \
    --no-php-ini \
    --define zend_extension=%{buildroot}%{php_ztsextdir}/%{pecl_name}.so \
    --modules | grep Xdebug
%endif

%if %{with_tests}
cd NTS
%if "%{php_version}" > "7.2"
# Know as failed upstream (travis)
rm tests/bug01258-php7.phpt
%endif
%ifarch ppc64 s390x
# Known as failed on big endian
rm tests/bug00806.phpt
rm tests/bug01305.phpt
rm tests/bug01312.phpt
rm tests/bug01335.phpt
rm tests/bug01512.phpt
rm tests/bug01516.phpt
%endif

: Upstream test suite NTS extension
# bug00886 is marked as slow as it uses a lot of disk space
SKIP_SLOW_TESTS=1 \
TEST_PHP_EXECUTABLE=%{_bindir}/php \
TEST_PHP_ARGS="-n $modules -d zend_extension=%{buildroot}%{php_extdir}/%{pecl_name}.so -d xdebug.auto_trace=0" \
NO_INTERACTION=1 \
REPORT_EXIT_STATUS=1 \
%{__php} -n run-tests.php --show-diff
%else
: Test suite disabled
%endif


%files
%license NTS/LICENSE
%doc %{pecl_docdir}/%{pecl_name}
%{_bindir}/debugclient
%{pecl_xmldir}/%{name}.xml

%config(noreplace) %{php_inidir}/%{ini_name}
%{php_extdir}/%{pecl_name}.so

%if %{with_zts}
%config(noreplace) %{php_ztsinidir}/%{ini_name}
%{php_ztsextdir}/%{pecl_name}.so
%endif


%changelog
* Tue Jan 23 2018 Remi Collet <remi@remirepo.net> - 2.6.0-0.5.RC2
- update to 2.6.0RC2
- undefine _strict_symbol_defs_build
- temporarily ignore 6 failed tests on big endian

* Fri Dec 29 2017 Remi Collet <remi@remirepo.net> - 2.6.0-0.4.beta1
- update to 2.6.0beta1

* Sun Dec  3 2017 Remi Collet <remi@remirepo.net> - 2.6.0-0.3.alpha1
- update to 2.6.0alpha1

* Wed Oct 18 2017 Remi Collet <remi@remirepo.net> - 2.6.0-0.2.20171018.33ed33d
- refresh with upstream fix for big endian
- enable test suite

* Tue Oct  3 2017 Remi Collet <remi@remirepo.net> - 2.6.0-0.1.20170925.9da805c
- update to 2.6.0-dev for PHP 7.2

* Thu Aug 03 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2.5.5-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2.5.5-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Thu Jun 22 2017 Remi Collet <remi@remirepo.net> - 2.5.5-1
- update to 2.5.5

* Mon May 15 2017 Remi Collet <remi@remirepo.net> - 2.5.4-1
- update to 2.5.4

* Mon Apr 24 2017 Remi Collet <remi@remirepo.net> - 2.5.3-1
- update to 2.5.3

* Mon Feb 27 2017 Remi Collet <remi@fedoraproject.org> - 2.5.1-2
- use uptream provided configuration with all settings

* Mon Feb 27 2017 Remi Collet <remi@fedoraproject.org> - 2.5.1-1
- update to 2.5.1

* Sat Feb 11 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2.5.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Mon Dec  5 2016 Remi Collet <remi@fedoraproject.org> - 2.5.0-1
- update to 2.5.0

* Mon Nov 14 2016 Remi Collet <remi@fedoraproject.org> - 2.5.0-0.1.RC1
- update to 2.5.0RC1 for PHP 7.1

* Tue Aug  2 2016 Remi Collet <remi@fedoraproject.org> - 2.4.1-1
- update to 2.4.1

* Mon Jun 27 2016 Remi Collet <remi@fedoraproject.org> - 2.4.0-2
- rebuild for https://fedoraproject.org/wiki/Changes/php70

* Tue Mar  8 2016 Remi Collet <remi@fedoraproject.org> - 2.4.0-1
- update to 2.4.0

* Sat Feb 13 2016 Remi Collet <remi@fedoraproject.org> - 2.3.3-3
- drop scriptlets (replaced by file triggers in php-pear)
- cleanup

* Thu Feb 04 2016 Fedora Release Engineering <releng@fedoraproject.org> - 2.3.3-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Fri Jun 19 2015 Remi Collet <remi@fedoraproject.org> - 2.3.3-1
- update to 2.3.3
- drop all patches, merged upstream

* Thu Jun 18 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.3.2-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Fri May 29 2015 Remi Collet <remi@fedoraproject.org> - 2.3.2-3
- add patch for exception code change (for phpunit)

* Wed May 27 2015 Remi Collet <remi@fedoraproject.org> - 2.3.2-2
- add patch for efree/str_efree in php 5.6
- add patch for virtual_file_ex in 5.6 #1214111

* Sun Mar 22 2015 Remi Collet <remi@fedoraproject.org> - 2.3.2-1
- Update to 2.3.2

* Wed Feb 25 2015 Remi Collet <remi@fedoraproject.org> - 2.3.1-1
- Update to 2.3.1

* Mon Feb 23 2015 Remi Collet <remi@fedoraproject.org> - 2.3.0-1
- Update to 2.3.0
- raise minimum php version to 5.4

* Thu Jan 22 2015 Remi Collet <remi@fedoraproject.org> - 2.2.7-1
- Update to 2.2.7

* Sun Nov 16 2014 Remi Collet <remi@fedoraproject.org> - 2.2.6-1
- Update to 2.2.6 (stable)

* Sun Aug 17 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.5-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Thu Jun 19 2014 Remi Collet <rcollet@redhat.com> - 2.2.5-3
- rebuild for https://fedoraproject.org/wiki/Changes/Php56

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.5-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Wed Apr 30 2014 Remi Collet <remi@fedoraproject.org> - 2.2.5-1
- Update to 2.2.5 (stable)

* Wed Apr 23 2014 Remi Collet <remi@fedoraproject.org> - 2.2.4-2
- add numerical prefix to extension configuration file
- drop uneeded full extension path

* Sun Mar 02 2014 Remi Collet <remi@fedoraproject.org> - 2.2.4-1
- Update to 2.2.4 (stable)
- move documentation in pecl_docdir
- cleanups

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.3-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Tue Jul 16 2013 Remi Collet <remi@fedoraproject.org> - 2.2.3-2
- adapt for SCL

* Wed May 22 2013 Remi Collet <remi@fedoraproject.org> - 2.2.3-1
- Update to 2.2.3

* Sun Mar 24 2013 Remi Collet <remi@fedoraproject.org> - 2.2.2-1
- update to 2.2.2 (stable)
- run buildconf for aarch64 support #926329
- modernize spec

* Fri Mar 22 2013 Remi Collet <rcollet@redhat.com> - 2.2.2-0.1.gitb1ce1e3
- update to 2.2.2dev for php 5.5
- rebuild for http://fedoraproject.org/wiki/Features/Php55
- also provides php-xdebug

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.1-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2.1-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Tue Jul 17 2012 Remi Collet <remi@fedoraproject.org> - 2.2.1-1
- Update to 2.2.1

* Fri Jun 22 2012 Remi Collet <remi@fedoraproject.org> - 2.2.0-2
- upstream patch for upstream bug #838/#839/#840

* Wed May 09 2012 Remi Collet <remi@fedoraproject.org> - 2.2.0-1
- Update to 2.2.0

* Sun Apr 29 2012 Remi Collet <remi@fedoraproject.org> - 2.2.0-0.3.RC2
- Update to 2.2.0RC2

* Sat Mar 17 2012 Remi Collet <remi@fedoraproject.org> - 2.2.0-0.2.RC1
- update to 2.2.0RC1
- enable ZTS build
- fix License which is PHP, with some renaming

* Fri Jan 20 2012 Remi Collet <remi@fedoraproject.org> - 2.2.0-0.1.gitd076740
- update to 2.2.0-dev, build against php 5.4

* Sat Jan 14 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.1.2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Thu Jul 28 2011 Remi Collet <Fedora@FamilleCollet.com> - 2.1.2-1
- update to 2.1.2
- fix provides filter for rpm 4.9
- improved description

* Wed Mar 30 2011 Remi Collet <Fedora@FamilleCollet.com> - 2.1.1-1
- update to 2.1.1
- patch reported version

* Wed Feb 09 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.1.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Sat Oct 23 2010 Remi Collet <Fedora@FamilleCollet.com> - 2.1.0-2
- add filter_provides to avoid private-shared-object-provides xdebug.so
- add %%check section (minimal load test)
- always use libedit

* Tue Jun 29 2010 Remi Collet <Fedora@FamilleCollet.com> - 2.1.0-1
- update to 2.1.0

* Mon Sep 14 2009 Christopher Stone <chris.stone@gmail.com> 2.0.5-1
- Upstream sync

* Sun Jul 26 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.4-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Sun Jul 12 2009 Remi Collet <Fedora@FamilleCollet.com> - 2.0.4-1
- update to 2.0.4 (bugfix + Basic PHP 5.3 support)

* Thu Feb 26 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.0.3-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Thu Oct 09 2008 Christopher Stone <chris.stone@gmail.com> 2.0.3-4
- Add code coverage patch (bz #460348)
- http://bugs.xdebug.org/bug_view_page.php?bug_id=0000344

* Thu Oct 09 2008 Christopher Stone <chris.stone@gmail.com> 2.0.3-3
- Revert last change

* Thu Oct 09 2008 Christopher Stone <chris.stone@gmail.com> 2.0.3-2
- Add php-xml to Requires (bz #464758)

* Thu May 22 2008 Christopher Stone <chris.stone@gmail.com> 2.0.3-1
- Upstream sync
- Clean up libedit usage
- Minor rpmlint fix

* Sun Mar 02 2008 Christopher Stone <chris.stone@gmail.com> 2.0.2-4
- Add %%{__pecl} to post/postun Requires

* Fri Feb 22 2008 Christopher Stone <chris.stone@gmail.com> 2.0.2-3
- %%define %%pecl_name to properly register package
- Install xml package description
- Add debugclient
- Many thanks to Edward Rudd (eddie@omegaware.com) (bz #432681)

* Wed Feb 20 2008 Fedora Release Engineering <rel-eng@fedoraproject.org> - 2.0.2-2
- Autorebuild for GCC 4.3

* Sun Nov 25 2007 Christopher Stone <chris.stone@gmail.com> 2.0.2-1
- Upstream sync

* Sun Sep 30 2007 Christopher Stone <chris.stone@gmail.com> 2.0.0-2
- Update to latest standards
- Fix encoding on Changelog

* Sat Sep 08 2007 Christopher Stone <chris.stone@gmail.com> 2.0.0-1
- Upstream sync
- Remove %%{?beta} tags

* Sun Mar 11 2007 Christopher Stone <chris.stone@gmail.com> 2.0.0-0.5.RC2
- Create directory to untar sources
- Use new ABI check for FC6
- Remove %%{release} from Provides

* Mon Jan 29 2007 Christopher Stone <chris.stone@gmail.com> 2.0.0-0.4.RC2
- Compile with $RPM_OPT_FLAGS
- Use $RPM_BUILD_ROOT instead of %%{buildroot}
- Fix license tag

* Mon Jan 15 2007 Christopher Stone <chris.stone@gmail.com> 2.0.0-0.3.RC2
- Upstream sync

* Sun Oct 29 2006 Christopher Stone <chris.stone@gmail.com> 2.0.0-0.2.RC1
- Upstream sync

* Wed Sep 06 2006 Christopher Stone <chris.stone@gmail.com> 2.0.0-0.1.beta6
- Remove Provides php-xdebug
- Fix Release
- Remove prior changelog due to Release number change
