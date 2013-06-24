#! /usr/bin/env python

import os
import shutil
import sys
import getopt
import subprocess
import ConfigParser

class BuildConfig:
    # Target directory.
    path     = ''
    prefix   = ''
    binutils = ''
    gcc      = ''
    glibc    = ''
    linux    = ''
    build    = ''
    version  = ''
    src_binutils = ''
    src_gcc      = ''
    src_glibc    = ''
    src_linux    = ''

    # Built-in configuration
    target       = ''
    triple       = ''
    fpu          = ''
    floatabi     = ''
	# --with-abi
    abi          = ''
	# --with-cpu
    cpu          = ''
	# --with-arch
    arch         = ''
    endian       = ''
    kernel_header = ''

    jobs         = ''
    def __init__(self):
        pass

builtin_aarch64 = {
    "triple" : "aarch64-linux-gnu",
    "kernel_header" : "arm64",
    "glibc"  : "2.17",
    "linux"  : "3.7.0",
    "binutils" : "2.23",
    "gcc"    : "4.8.0",
    "default-glibc" : "2.17",
    "default-linux" : "3.9.4",
    "default-binutils" : "2.23.2",
    "default-gcc" : "4.8.1",
}

builtin_aarch64eb = {
    "triple" : "aarch64_be-linux-gnu",
    "kernel_header" : "arm64",
    "glibc"  : "2.17",
    "linux"  : "3.7.0",
    "binutils" : "2.23",
    "gcc"    : "4.8.0",
    "default-glibc" : "2.17",
    "default-linux" : "3.9.4",
    "default-binutils" : "2.23.2",
    "default-gcc" : "4.8.1",
}

builtinTarget = {
    "aarch64" : builtin_aarch64,
    "aarch64eb" : builtin_aarch64eb,
}

def checkReturnCode(ret, msg):
    if ret != 0:
        print('Error!')
        print('Message :' + msg)
        sys.exit(1)

def checkStrVersion(minVersion, curVersion):
    minVerList = minVersion.split('.')
    curVerList = curVersion.split('.')
    if len(curVerList) > 3:
        print('Wrong version :' + curVersion)
        sys.exit(1)
    i = 0;
    while i < len(minVerList) and i < 3:
        if int(minVerList[i]) < int(curVerList[i]):
            return False
        i = i + 1
    return True

def checkVersion(buildConfig, config):
    if not checkStrVersion(config.gcc, buildConfig.gcc):
        print('Current version of gcc do not work!')
        sys.exit(1)
    if not checkStrVersion(config.glibc, buildConfig.glibc):
        print('Current version of glibc do not work!')
        sys.exit(1)
    if not checkStrVersion(config.binutils, buildConfig.binutils):
        print('Current version of binutils do not work!')
        sys.exit(1)
    if not checkStrVersion(config.linux, buildConfig.linux):
        print('Current version of linux do not work!')
        sys.exit(1)

def useBuiltinConfig(buildConfig):
    config = builtinTarget[buildConfig.target]
    if buildConfig.version == 'default':
        buildConfig.gcc = config['default-gcc']
        buildConfig.glibc = config['default-glibc']
        buildConfig.linux = config['default-linux']
        buildConfig.binutils = config['default-binutils']
    else:
        checkVersion(buildConfig, config)
    buildConfig.triple = config['triple']
    buildConfig.kernel_header = config['kernel_header']

def configureTarget(buildConfig):
    if buildConfig.jobs == '':
        buildConfig.jobs = '-j10'
    else:
        if buildConfig.jobs[0:2] != '-j':
            buildConfig.jobs = '-j' + str(int(buildConfig.jobs))
        else:
            buildConfig.jobs = '-j' + str(int(buildConfig.jobs[2:]))
    if buildConfig.target != '' and buildConfig.target in builtinTarget:
        useBuiltinConfig(buildConfig)
    else:
        print('error now')
        print(buildConfig.target)
        print(builtinTarget)
		

def buildBinutils(buildConfig):
    cwd = os.getcwd()

    build = buildConfig.build + '/build-binutils'
    if os.path.exists(build):
        shutil.rmtree(build)
    try:
        os.mkdir(build)
        os.chdir(build)
    except:
        print('Error when building binutils.')
        sys.exit(1)
    configScript = buildConfig.src_binutils + '/configure'
    target = '--target=' + buildConfig.triple
    prefix = '--prefix=' + buildConfig.prefix
    ret = subprocess.call([configScript, target, prefix])
    checkReturnCode(ret, 'configure binutils')
    ret = subprocess.call(['make', buildConfig.jobs])
    checkReturnCode(ret, 'make binutils')
    ret = subprocess.call(['make', 'install'])
    checkReturnCode(ret, 'install binutils')

    os.chdir(cwd)

def buildGccPass1(buildConfig):
    cwd = os.getcwd()
    build = buildConfig.build + '/build-gcc1'
    if os.path.exists(build):
        shutil.rmtree(build)
    try:
        os.mkdir(build)
        os.chdir(build)
    except:
        print('Error when building gcc pass 1.')
        sys.exit(1)
    configScript = buildConfig.src_gcc + '/configure'
    target = '--target=' + buildConfig.triple
    prefix = '--prefix=' + buildConfig.prefix

    ret = subprocess.call([configScript, target, prefix,
            '--enable-languages=c', '--disable-shared', '--disable-nls', '--disable-threads',
            '--disable-libssp', '--without-headers', '--disable-decimal-float',
            '--disable-libgomp', '--disable-libmudflap', '--disable-multilib',
            '--with-gnu-ld', '--with-gnu-as', '--with-newlib'])
    checkReturnCode(ret, 'configure gcc pass 1')
    ret = subprocess.call(['make','all-gcc' ,'all-target-libgcc' , buildConfig.jobs])
    checkReturnCode(ret, 'make gcc pass 1')
    ret = subprocess.call(['make', 'install-gcc', 'install-target-libgcc'])
    checkReturnCode(ret, 'install gcc pass 1')

    os.chdir(cwd)


def installKernelHeader(buildConfig):
    cwd = os.getcwd()
    os.chdir(buildConfig.src_linux)
    ret = subprocess.call(['make', 'mrproper'])
    checkReturnCode(ret, 'make mrproper')
    ret = subprocess.call(['make', 'ARCH='+buildConfig.kernel_header, 'headers_check'])
    checkReturnCode(ret, 'make headers check')
    ret = subprocess.call(['make', 'ARCH='+buildConfig.kernel_header, 'INSTALL_HDR_PATH='+buildConfig.prefix, 'headers_install'])
    checkReturnCode(ret, 'install kernel header')

    os.chdir(cwd)

def buildGlibc(buildConfig):
    cwd = os.getcwd()

    build = buildConfig.build + '/build-glibc'
    if os.path.exists(build):
        shutil.rmtree(build)
    try:
        os.mkdir(build)
        os.chdir(build)
    except:
        print('Error when building binutils.')
        sys.exit(1)
    configScript = buildConfig.src_glibc + '/configure'
    target = '--host=' + buildConfig.triple
    prefix = '--prefix=' + buildConfig.prefix
    header = os.path.abspath(buildConfig.prefix + '/include')
    binutils = os.path.abspath(buildConfig.prefix + '/bin')
    ret = subprocess.call([configScript, target, prefix, '--enable-add-ons',
            '--with-headers='+header, '--with-binutils='+binutils])
    checkReturnCode(ret, 'configure glibc')
    ret = subprocess.call(['make', buildConfig.jobs])
    checkReturnCode(ret, 'make glibc')
    ret = subprocess.call(['make', 'install'])
    checkReturnCode(ret, 'install glibc')

    os.chdir(cwd)

def buildGccPass2(buildConfig):
    cwd = os.getcwd()
    build = buildConfig.build + '/build-gcc2'
    if os.path.exists(build):
        shutil.rmtree(build)
    try:
        os.mkdir(build)
        os.chdir(build)
    except:
        print('Error when building gcc pass 2.')
        sys.exit(1)
    configScript = buildConfig.src_gcc + '/configure'
    target = '--target=' + buildConfig.triple
    prefix = '--prefix=' + buildConfig.prefix

    ret = subprocess.call([configScript, target, prefix,
            '--enable-languages=c,c++', '--enable-shared', '--disable-nls', '--enable-c99',
            '--enable-long-long', '--disable-multilib'])
    checkReturnCode(ret, 'configure gcc pass 2')
    ret = subprocess.call(['make', buildConfig.jobs])
    checkReturnCode(ret, 'make gcc pass 2')
    ret = subprocess.call(['make', 'install'])
    checkReturnCode(ret, 'install gcc pass 2')

    os.chdir(cwd)

def hackMoveTo(current, target):
    fname = 'ldscripts'
    if os.path.exists(current + '/' + fname):
        os.rename(current + '/' + fname, target + '/' + fname)
    shutil.rmtree(current)

def hackLibPath(buildConfig):
    targetLib = os.path.abspath(buildConfig.prefix + '/' + buildConfig.triple)
    rootLib   = os.path.abspath(buildConfig.prefix + '/lib')
    rootLib64 = os.path.abspath(buildConfig.prefix + '/lib64')
    include   = os.path.abspath(buildConfig.prefix + '/include')
    cwd = os.getcwd()
    try:
        os.chdir(targetLib)
        if os.path.exists('lib'):
            hackMoveTo('lib', rootLib)
        os.symlink('../lib', 'lib')
        print(targetLib)
        if os.path.exists('lib64'):
            hackMoveTo('lib64', rootLib64)
        os.symlink('../lib64', 'lib64')
        if os.path.exists('include'):
            hackMoveTo('include', include)
        os.symlink('../include', 'include')
    except:
        print('Error when hacking lib path')
        sys.exit(1)
    os.chdir(cwd)

def uncompress(tarball, build, targetDir):
    source = build + '/' + targetDir
    if os.path.exists(source):
        print('Skip ' + tarball)
        return
    print('Uncompress ' + os.path.basename(tarball))
    ret = subprocess.call(['tar', 'xf', tarball, '-C', build])
    if ret == 0:
        print('Done')
    else:
        print('Uncompress error!')
        sys.exit(1)

def downloadTarball(name, version, target):
    return ''

def getSourceTarball(name, version, target):
    fullName = name + '-' + version
    path = target + '/' + fullName + '.tar.bz2'
    if os.path.exists(path):
        return path, fullName
    path = target + '/' + fullName + '.tar.xz'
    if os.path.exists(path):
        return path, fullName
    path = target + '/' + fullName + '.tar.gz'
    if os.path.exists(path):
        return path, fullName
    tarball = downloadTarball(name, version, target)
    if not os.path.exists(tarball):
        print('Error! Could not find ' + tarball)
        print('name =' + name + '; version =' + version)
        sys.exit(1)
    return tarball, fullName

def getSource(buildConfig):
    downloads = buildConfig.path + '/' + 'downloads'
    build     = buildConfig.path + '/' + 'build'
    try:
        if not os.path.exists(downloads):
            os.mkdir(downloads)
        if not os.path.exists(downloads):
            os.mkdir(build)
    except:
        print('Error when creating directory!')
        sys.exit(1)
    tar_binutils, src_binutils = getSourceTarball('binutils', buildConfig.binutils, downloads)
    uncompress(tar_binutils, build, src_binutils)
    tar_gcc, src_gcc = getSourceTarball('gcc',   buildConfig.gcc, downloads)
    uncompress(tar_gcc, build, src_gcc)
    tar_glibc, src_glibc = getSourceTarball('glibc', buildConfig.glibc, downloads)
    uncompress(tar_glibc, build, src_glibc)
    tar_linux, src_linux = getSourceTarball('linux', buildConfig.linux, downloads)
    uncompress(tar_linux, build, src_linux)

    buildConfig.build = os.path.abspath(build)
    buildConfig.src_binutils = os.path.abspath(build + '/' + src_binutils)
    buildConfig.src_gcc      = os.path.abspath(build + '/' + src_gcc)
    buildConfig.src_glibc    = os.path.abspath(build + '/' + src_glibc)
    buildConfig.src_linux    = os.path.abspath(build + '/' + src_linux)


def readOptions(config, section, name):
    try:
        return config.get(section, name)
    except:
        return ''

def readConfigFile(path):
    config = ConfigParser.ConfigParser()
    files = config.read(path)
    if not files:
        print("Could not read config file correcttly!")
        sys.exit(1)
    section = 'default'
    buildConfig = BuildConfig()
    buildConfig.binutils = readOptions(config, section, 'binutils')
    buildConfig.gcc      = readOptions(config, section, 'gcc')
    buildConfig.glibc    = readOptions(config, section, 'glibc')
    buildConfig.linux    = readOptions(config, section, 'linux')
    buildConfig.path     = readOptions(config, section, 'path')
    buildConfig.prefix   = readOptions(config, section, 'prefix')
    buildConfig.version  = readOptions(config, section, 'version')

    buildConfig.target   = readOptions(config, section, 'target')
    buildConfig.triple   = readOptions(config, section, 'triple')
    buildConfig.fpu      = readOptions(config, section, 'fpu')
    buildConfig.floatabi = readOptions(config, section, 'floatabi')
    buildConfig.abi      = readOptions(config, section, 'abi')
    buildConfig.cpu      = readOptions(config, section, 'cpu')
    buildConfig.arch     = readOptions(config, section, 'arch')

    buildConfig.jobs     = readOptions(config, section, 'jobs')

    if buildConfig.path == '':
        buildConfig.path = '.'
    if buildConfig.prefix == '':
        buildConfig.prefix = buildConfig.path + '/' + 'install'
    buildConfig.path = os.path.abspath(buildConfig.path)
    buildConfig.prefix = os.path.abspath(buildConfig.prefix)
    if not os.path.exists(buildConfig.path):
        print('Target directory does not exist!')
        sys.exit(1)
    return buildConfig

def setEnv():
    os.unsetenv('C_INCLUDE_PATH')
    os.unsetenv('CPLUS_INCLUDE_PATH')

def setEnvPath(buildConfig):
    oldPath = os.environ['PATH']
    prefix  = buildConfig.prefix 
    newBin  = os.path.abspath(prefix + '/bin')
    newPath = newBin + ':' + oldPath
    os.environ['PATH'] = newPath

def main():
    opts, others = getopt.getopt(sys.argv[1:], 'h', ['config=', 'skip='])
    configFile = ''
    skipList = []
    for item in opts:
        if item[0] == '--config':
            configFile = item[1]
        elif item[0] == '--skip':
            skipList.append(item[1])

    if configFile == '':
        print("No config file specified!")
        sys.exit(1)
    buildConfig = readConfigFile(configFile)
    configureTarget(buildConfig)
    # Get source code first.
    getSource(buildConfig)

    setEnv()
    if not 'binutils' in skipList and not 'all' in skipList:
        buildBinutils(buildConfig)
    setEnvPath(buildConfig)

    if not 'gcc1' in skipList and not 'all' in skipList:
        buildGccPass1(buildConfig)

    if not 'header' in skipList and not 'all' in skipList:
        installKernelHeader(buildConfig)

    if not 'glibc' in skipList and not 'all' in skipList:
        buildGlibc(buildConfig)
    # I don't known why this hack should be done.
    hackLibPath(buildConfig)
    
    if not 'gcc2' in skipList and not 'all' in skipList:
        buildGccPass2(buildConfig)

if __name__ == "__main__":
    main()
